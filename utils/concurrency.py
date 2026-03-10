"""Shared concurrency heuristics for demo/CLI workflows."""

from __future__ import annotations

from utils.pipeline_state import normalize_task_name
from utils.retrieval_settings import normalize_retrieval_setting


def compute_effective_concurrency(
    concurrency_mode: str,
    max_concurrent: int,
    total_candidates: int,
    *,
    task_name: str = "diagram",
    retrieval_setting: str = "auto",
    exp_mode: str = "dev_planner_critic",
    provider: str = "gemini",
) -> int:
    """Compute the effective candidate concurrency for the current workload."""
    safe_max = max(1, int(max_concurrent))
    safe_total = max(1, int(total_candidates))
    requested = min(safe_max, safe_total)

    normalized_mode = str(concurrency_mode or "").strip().lower()
    if normalized_mode != "auto":
        return requested

    # Aggressive auto mode: honor the user's candidate/max settings directly.
    # We still keep the normalizers for a stable signature shared by CLI/demo code.
    normalize_task_name(task_name)
    normalize_retrieval_setting(retrieval_setting)
    str(exp_mode or "").strip().lower()
    str(provider or "gemini").strip().lower()
    return requested
