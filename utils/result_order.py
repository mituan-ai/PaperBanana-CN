"""Helpers for stable candidate metadata and deterministic result ordering."""

from __future__ import annotations

from typing import Any, Iterable


def prepare_input_payload(
    payload: dict[str, Any] | None,
    input_index: int,
) -> dict[str, Any]:
    prepared = dict(payload or {})
    prepared.setdefault("input_index", int(input_index))
    prepared.setdefault("candidate_id", int(input_index))
    return prepared


def get_candidate_id(result: dict[str, Any] | None, fallback: Any = None) -> Any:
    if not isinstance(result, dict):
        return fallback

    for key in ("candidate_id", "input_index", "id"):
        value = result.get(key)
        if value not in (None, ""):
            return value
    return fallback


def get_candidate_display_index(result: dict[str, Any] | None, fallback_index: int = 0) -> int:
    if isinstance(result, dict):
        for key in ("input_index", "candidate_id"):
            value = result.get(key)
            if isinstance(value, int):
                return value + 1
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip()) + 1
    return max(1, int(fallback_index) + 1)


def format_candidate_display_label(
    result: dict[str, Any] | None,
    *,
    fallback_index: int = 0,
    prefix: str = "候选",
) -> str:
    return f"{prefix} {get_candidate_display_index(result, fallback_index):02d}"


def _normalize_order_value(value: Any) -> tuple[int, Any]:
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, int):
        return (0, value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return (0, int(stripped))
        if stripped:
            return (1, stripped)
    if value not in (None, ""):
        return (2, str(value))
    return (3, "")


def result_sort_key(result: dict[str, Any] | None, fallback_index: int = 0) -> tuple[Any, ...]:
    if not isinstance(result, dict):
        return (4, fallback_index, fallback_index)

    input_index = result.get("input_index")
    if input_index not in (None, ""):
        normalized = _normalize_order_value(input_index)
        return (0, normalized[0], normalized[1], fallback_index)

    candidate_id = result.get("candidate_id")
    if candidate_id not in (None, ""):
        normalized = _normalize_order_value(candidate_id)
        return (1, normalized[0], normalized[1], fallback_index)

    result_id = result.get("id")
    if result_id not in (None, ""):
        normalized = _normalize_order_value(result_id)
        return (2, normalized[0], normalized[1], fallback_index)

    return (3, fallback_index, fallback_index)


def sort_results_stably(results: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    indexed_results = list(enumerate(list(results or [])))
    indexed_results.sort(key=lambda pair: result_sort_key(pair[1], pair[0]))
    return [item for _, item in indexed_results]
