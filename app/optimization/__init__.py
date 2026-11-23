"""Compare stored experiments and name the larger client-clock phase.

``compare`` returns the deltas, the setting differences, both phase labels,
and the stored sample ranges. ``phase_label`` names ``prefill``, ``decode``,
``even``, or no value.

This package does not call Ollama, does not call ``psutil``, does not open
SQLite, and does not call ``summarize``.
"""

from app.optimization.comparison import compare
from app.optimization.experiments import phase_label

__all__ = ["compare", "phase_label"]
