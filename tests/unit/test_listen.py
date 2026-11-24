"""Listen address and the CI workflow file.

The listen tests pass a mapping. They do not read the process environment.
Ollama is not contacted. No test asserts a latency number from a live server.
No test reads a findings file.
"""

from __future__ import annotations

from pathlib import Path

from app.main import listen_settings

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_absent_variables_keep_the_local_default() -> None:
    assert listen_settings({}) == ("127.0.0.1", 8000)


def test_host_override_can_set_all_interfaces() -> None:
    assert listen_settings({"INFERBENCH_HOST": "0.0.0.0"}) == ("0.0.0.0", 8000)


def test_blank_variables_keep_the_local_default() -> None:
    assert listen_settings({"INFERBENCH_HOST": " ", "INFERBENCH_PORT": ""}) == (
        "127.0.0.1",
        8000,
    )


def test_port_override_stays_with_the_local_host() -> None:
    assert listen_settings({"INFERBENCH_PORT": " 9000 "}) == ("127.0.0.1", 9000)


def test_workflow_lists_pytest_frontend_and_image_build() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "python-version: \"3.13\"" in text
    assert "pip install -r requirements.txt -r requirements-dev.txt" in text
    assert "python -m pytest" in text
    assert "working-directory: frontend" in text
    assert "npm ci" in text
    assert "npm test" in text
    assert "npm run build" in text
    assert "docker compose build" in text
    assert "docker compose up" not in text
    assert "ollama pull" not in text
