"""Load curated retrieval profiles with backward compatibility."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from utils.dataset_paths import get_reference_file_path, get_task_data_dir
from utils.retrieval_settings import DEFAULT_CURATED_PROFILE, normalize_curated_profile_name


LEGACY_MANUAL_REFERENCE_FILENAME = "agent_selected_12.json"
CURATED_PROFILE_DIRNAME = "manual_profiles"


@dataclass(frozen=True)
class CuratedReferenceProfile:
    profile_name: str
    source_path: Path
    selected_ids: list[str]
    examples: list[dict[str, Any]]
    missing_ids: list[str] = field(default_factory=list)
    is_legacy_file: bool = False


def get_curated_profile_dir(
    dataset_name: str | None,
    task_name: str,
    *,
    work_dir: str | Path | None = None,
) -> Path:
    return get_task_data_dir(dataset_name, task_name, work_dir=work_dir) / CURATED_PROFILE_DIRNAME


def get_curated_profile_path(
    dataset_name: str | None,
    task_name: str,
    *,
    profile_name: str = DEFAULT_CURATED_PROFILE,
    work_dir: str | Path | None = None,
) -> Path:
    normalized_profile = normalize_curated_profile_name(profile_name)
    return get_curated_profile_dir(dataset_name, task_name, work_dir=work_dir) / f"{normalized_profile}.json"


def get_legacy_manual_reference_path(
    dataset_name: str | None,
    task_name: str,
    *,
    work_dir: str | Path | None = None,
) -> Path:
    return get_task_data_dir(dataset_name, task_name, work_dir=work_dir) / LEGACY_MANUAL_REFERENCE_FILENAME


def iter_curated_profile_candidate_paths(
    dataset_name: str | None,
    task_name: str,
    *,
    profile_name: str = DEFAULT_CURATED_PROFILE,
    work_dir: str | Path | None = None,
) -> list[Path]:
    normalized_profile = normalize_curated_profile_name(profile_name)
    candidates = [
        get_curated_profile_path(
            dataset_name,
            task_name,
            profile_name=normalized_profile,
            work_dir=work_dir,
        )
    ]
    if normalized_profile == DEFAULT_CURATED_PROFILE:
        candidates.append(
            get_legacy_manual_reference_path(
                dataset_name,
                task_name,
                work_dir=work_dir,
            )
        )
    return candidates


def find_curated_profile_path(
    dataset_name: str | None,
    task_name: str,
    *,
    profile_name: str = DEFAULT_CURATED_PROFILE,
    work_dir: str | Path | None = None,
) -> Path | None:
    for candidate in iter_curated_profile_candidate_paths(
        dataset_name,
        task_name,
        profile_name=profile_name,
        work_dir=work_dir,
    ):
        if candidate.exists():
            return candidate
    return None


def _load_reference_pool_map(
    dataset_name: str | None,
    task_name: str,
    *,
    work_dir: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    ref_file = get_reference_file_path(dataset_name, task_name, work_dir=work_dir)
    if not ref_file.exists():
        return {}
    with open(ref_file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return {
        str(item.get("id")).strip(): item
        for item in payload
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }


def _normalize_selected_ids(values: Any) -> list[str]:
    normalized_ids: list[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if text:
            normalized_ids.append(text)
    return normalized_ids


def _normalize_examples(values: Any) -> list[dict[str, Any]]:
    examples = list(values or [])
    if any(not isinstance(item, dict) for item in examples):
        raise ValueError("Curated reference examples must be JSON objects.")
    return [dict(item) for item in examples]


def _parse_profile_payload(payload: Any) -> tuple[str, list[str], list[dict[str, Any]]]:
    profile_name = DEFAULT_CURATED_PROFILE
    selected_ids: list[str] = []
    examples: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        profile_name = normalize_curated_profile_name(payload.get("profile_name"))
        if isinstance(payload.get("examples"), list):
            examples = _normalize_examples(payload.get("examples"))
        else:
            id_values = (
                payload.get("selected_ids")
                or payload.get("ids")
                or payload.get("reference_ids")
                or payload.get("top10_references")
                or []
            )
            selected_ids = _normalize_selected_ids(id_values)
    elif isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            examples = _normalize_examples(payload)
        else:
            selected_ids = _normalize_selected_ids(payload)
    else:
        raise ValueError("Curated retrieval profile must be a JSON object or array.")

    return profile_name, selected_ids, examples


def load_curated_reference_profile(
    dataset_name: str | None,
    task_name: str,
    *,
    profile_name: str = DEFAULT_CURATED_PROFILE,
    work_dir: str | Path | None = None,
    limit: int = 10,
) -> CuratedReferenceProfile:
    source_path = find_curated_profile_path(
        dataset_name,
        task_name,
        profile_name=profile_name,
        work_dir=work_dir,
    )
    if source_path is None:
        raise FileNotFoundError(
            f"No curated retrieval profile found for dataset={dataset_name!r} task={task_name!r} "
            f"profile={normalize_curated_profile_name(profile_name)!r}."
        )

    with open(source_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    parsed_profile_name, selected_ids, examples = _parse_profile_payload(payload)
    normalized_profile_name = normalize_curated_profile_name(profile_name)
    if parsed_profile_name != DEFAULT_CURATED_PROFILE:
        normalized_profile_name = parsed_profile_name

    missing_ids: list[str] = []
    if not examples:
        reference_pool = _load_reference_pool_map(dataset_name, task_name, work_dir=work_dir)
        examples = []
        for ref_id in selected_ids:
            item = reference_pool.get(ref_id)
            if item is None:
                missing_ids.append(ref_id)
                continue
            examples.append(item)

    examples = examples[: max(1, int(limit))]
    selected_ids = _normalize_selected_ids(
        item.get("id") for item in examples if isinstance(item, dict)
    )

    return CuratedReferenceProfile(
        profile_name=normalized_profile_name,
        source_path=source_path,
        selected_ids=selected_ids,
        examples=examples,
        missing_ids=missing_ids,
        is_legacy_file=source_path.name == LEGACY_MANUAL_REFERENCE_FILENAME,
    )
