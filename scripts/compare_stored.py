"""Compare stored experiments and write analysis findings.

This file is not a pytest module. It reads the three SQLite files already
on disk. It does not construct an Ollama adapter. It does not call
``generate``, ``generate_stream``, ``show_model``, or ``list_models``. It
does not download a model. It does not call ``summarize``. It does not
delete or rewrite the SQLite files.
"""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.repository import StoredExperiment, load_experiments
from app.optimization.comparison import Comparison, compare

GEMMA = "gemma3:1b"
QWEN = "qwen3.5:2b"
SHORT = "short_prompt_short_output"
WORKLOAD_CANDIDATES = (
    "long_prompt_short_output",
    "short_prompt_long_output",
    "long_prompt_long_output",
)
MODEL_PROFILES = (SHORT,) + WORKLOAD_CANDIDATES
SUMMARY_FIELDS = (
    "average_ms",
    "median_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "error_rate",
    "generation_throughput_tps",
    "request_throughput_rps",
)

SERVING_DB = "experiments/results/serving-config.sqlite"
WORKLOAD_DB = "experiments/results/workload-sensitivity.sqlite"
MODEL_DB = "experiments/results/model-comparison.sqlite"
FINDINGS_PATH = ROOT / "docs" / "analysis-findings.md"


class MatchError(Exception):
    """A stored file or a required pair cannot be used."""


@dataclass(frozen=True)
class StoredPair:
    """One baseline and one candidate the caller named."""

    database_file: str
    baseline: StoredExperiment
    candidate: StoredExperiment
    cross_model: bool


def main() -> int:
    """Write the findings file, or exit non-zero without writing it."""
    try:
        loaded = _load_all()
        pairs = _pairs(loaded)
        text = _findings(loaded, pairs)
    except MatchError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    FINDINGS_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {FINDINGS_PATH.relative_to(ROOT).as_posix()} from {len(pairs)} stored pairs")
    return 0


def _load_all() -> dict[str, tuple[StoredExperiment, ...]]:
    loaded: dict[str, tuple[StoredExperiment, ...]] = {}
    for relative in (SERVING_DB, WORKLOAD_DB, MODEL_DB):
        path = ROOT / relative
        if not path.is_file():
            raise MatchError(f"missing file: {relative}")
        loaded[relative] = _load(path)
    return loaded


def _load(path: Path) -> tuple[StoredExperiment, ...]:
    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA query_only = ON")
        return connection

    engine = create_engine("sqlite://", creator=connect)
    try:
        with Session(engine) as session:
            return load_experiments(session)
    finally:
        engine.dispose()


def _pairs(loaded: dict[str, tuple[StoredExperiment, ...]]) -> tuple[StoredPair, ...]:
    serving = _serving_pairs(loaded[SERVING_DB], SERVING_DB)
    workload = _workload_pairs(loaded[WORKLOAD_DB], WORKLOAD_DB)
    model = _model_pairs(loaded[MODEL_DB], MODEL_DB)
    return tuple(serving + workload + model)


def _serving_pairs(rows: Sequence[StoredExperiment], database_file: str) -> list[StoredPair]:
    pairs: list[StoredPair] = []
    for model in (GEMMA, QWEN):
        pool = [
            row
            for row in rows
            if row.snapshot.model == model and row.snapshot.profile_name == SHORT
        ]
        baseline = _one(
            [
                row
                for row in pool
                if row.snapshot.concurrency == 1 and row.snapshot.num_thread is None
            ],
            f"{database_file} baseline {model} {SHORT} concurrency 1 num_thread null",
        )
        candidates = [row for row in pool if row.experiment_id != baseline.experiment_id]
        if not candidates:
            raise MatchError(f"missing match: {database_file} candidates for {model} {SHORT}")
        for candidate in candidates:
            pairs.append(
                StoredPair(
                    database_file=database_file,
                    baseline=baseline,
                    candidate=candidate,
                    cross_model=False,
                )
            )
    return pairs


def _workload_pairs(rows: Sequence[StoredExperiment], database_file: str) -> list[StoredPair]:
    baseline = _one(
        [
            row
            for row in rows
            if row.snapshot.model == GEMMA and row.snapshot.profile_name == SHORT
        ],
        f"{database_file} baseline {GEMMA} {SHORT}",
    )
    pairs: list[StoredPair] = []
    for profile in WORKLOAD_CANDIDATES:
        candidate = _one(
            [
                row
                for row in rows
                if row.snapshot.model == GEMMA and row.snapshot.profile_name == profile
            ],
            f"{database_file} candidate {GEMMA} {profile}",
        )
        pairs.append(
            StoredPair(
                database_file=database_file,
                baseline=baseline,
                candidate=candidate,
                cross_model=False,
            )
        )
    return pairs


def _model_pairs(rows: Sequence[StoredExperiment], database_file: str) -> list[StoredPair]:
    pairs: list[StoredPair] = []
    for profile in MODEL_PROFILES:
        baseline = _one(
            [
                row
                for row in rows
                if row.snapshot.model == GEMMA and row.snapshot.profile_name == profile
            ],
            f"{database_file} baseline {GEMMA} {profile}",
        )
        candidate = _one(
            [
                row
                for row in rows
                if row.snapshot.model == QWEN and row.snapshot.profile_name == profile
            ],
            f"{database_file} candidate {QWEN} {profile}",
        )
        pairs.append(
            StoredPair(
                database_file=database_file,
                baseline=baseline,
                candidate=candidate,
                cross_model=True,
            )
        )
    return pairs


def _one(rows: Sequence[StoredExperiment], label: str) -> StoredExperiment:
    if len(rows) == 0:
        raise MatchError(f"missing match: {label}")
    if len(rows) != 1:
        raise MatchError(f"match is not unique: {label}")
    return rows[0]


def _findings(
    loaded: dict[str, tuple[StoredExperiment, ...]],
    pairs: Sequence[StoredPair],
) -> str:
    counts = sorted(
        {
            row.snapshot.measured_count
            for rows in loaded.values()
            for row in rows
        }
    )
    if counts == [3]:
        measured = "The measured count on these stored runs is 3."
    else:
        shown = ", ".join(str(count) for count in counts)
        measured = f"The measured counts on these stored runs are {shown}."
    lines = [
        "# Analysis findings",
        "",
        "These figures were loaded from the three stored SQLite files through `load_experiments` and `compare`.",
        "No new Ollama call was made.",
        "Step 9 was not run.",
        measured,
        "A delta is the candidate's stored aggregate minus the baseline's stored aggregate.",
        "An omitted num_thread is written as omitted, not as 0.",
        "A Qwen-versus-Gemma pair is a cross-model comparison and not a quantization result.",
        "Thinking on versus off was not run.",
        "This file does not name a winner or recommend a setting.",
        "A CPU sample of 0 stays a sample.",
        "",
    ]
    for pair in pairs:
        lines.extend(_pair_lines(pair, compare(pair.baseline, pair.candidate)))
    return "\n".join(lines) + "\n"


def _pair_lines(pair: StoredPair, result: Comparison) -> list[str]:
    baseline = pair.baseline
    candidate = pair.candidate
    file_name = Path(pair.database_file).name
    lines = [
        f"## {file_name} / baseline {baseline.experiment_id} / candidate {candidate.experiment_id}",
        "",
        f"- Database file: {file_name}",
        f"- Baseline experiment id: {baseline.experiment_id}",
        f"- Candidate experiment id: {candidate.experiment_id}",
        f"- Baseline model: {baseline.snapshot.model}",
        f"- Candidate model: {candidate.snapshot.model}",
        f"- Baseline profile name: {_show(baseline.snapshot.profile_name)}",
        f"- Candidate profile name: {_show(candidate.snapshot.profile_name)}",
        f"- Baseline concurrency: {baseline.snapshot.concurrency}",
        f"- Candidate concurrency: {candidate.snapshot.concurrency}",
        f"- Baseline num_thread: {_thread(baseline.snapshot.num_thread)}",
        f"- Candidate num_thread: {_thread(candidate.snapshot.num_thread)}",
        f"- Baseline think: {_think(baseline.snapshot.think)}",
        f"- Candidate think: {_think(candidate.snapshot.think)}",
    ]
    if pair.cross_model:
        lines.append("- This pair is a cross-model comparison.")
    lines.append("- Differing settings:")
    if result.setting_differences:
        for difference in result.setting_differences:
            baseline_value = _setting_value(difference.field, difference.baseline)
            candidate_value = _setting_value(difference.field, difference.candidate)
            lines.append(f"  - {difference.field}: {baseline_value} versus {candidate_value}")
    else:
        lines.append("  - none")
    for name in SUMMARY_FIELDS:
        lines.append(f"- Baseline {name}: {_show(getattr(baseline.summary, name))}")
        lines.append(f"- Candidate {name}: {_show(getattr(candidate.summary, name))}")
        lines.append(f"- {name} delta: {_show(getattr(result, name + '_delta'))}")
    lines.extend(
        [
            f"- Baseline phase label: {_show(result.baseline_phase_label)}",
            f"- Candidate phase label: {_show(result.candidate_phase_label)}",
            f"- Baseline sample count: {result.baseline_samples.sample_count}",
            f"- Baseline min system CPU percent: {_show(result.baseline_samples.cpu_percent_min)}",
            f"- Baseline max system CPU percent: {_show(result.baseline_samples.cpu_percent_max)}",
            f"- Baseline min system RAM used: {_show(result.baseline_samples.system_ram_used_bytes_min)}",
            f"- Baseline max system RAM used: {_show(result.baseline_samples.system_ram_used_bytes_max)}",
            f"- Candidate sample count: {result.candidate_samples.sample_count}",
            f"- Candidate min system CPU percent: {_show(result.candidate_samples.cpu_percent_min)}",
            f"- Candidate max system CPU percent: {_show(result.candidate_samples.cpu_percent_max)}",
            f"- Candidate min system RAM used: {_show(result.candidate_samples.system_ram_used_bytes_min)}",
            f"- Candidate max system RAM used: {_show(result.candidate_samples.system_ram_used_bytes_max)}",
        ]
    )
    if result.sign_sentence is not None:
        lines.append(f"- Sign sentence: {result.sign_sentence}")
    lines.append("")
    return lines


def _thread(value: int | None) -> str:
    """An omitted thread value is omitted. It is not the integer 0."""
    if value is None:
        return "omitted"
    return str(value)


def _think(value: bool | None) -> str:
    """An omitted think flag is omitted. It is not false."""
    if value is None:
        return "omitted"
    if value is False:
        return "false"
    return "true"


def _setting_value(field: str, value: str | int | bool | None) -> str:
    if field == "num_thread" and value is None:
        return "omitted"
    if field == "think" and value is None:
        return "omitted"
    return _show(value)


def _show(value: object) -> str:
    """Format one stored field. None stays unset."""
    if value is None:
        return "unset"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
