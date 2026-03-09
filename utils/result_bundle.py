"""Shared helpers for portable result bundle files and legacy result loading."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

from utils.dataset_paths import DEFAULT_DATASET_NAME, normalize_dataset_name
from utils.pipeline_state import detect_task_type_from_result, normalize_task_name
from utils.run_report import build_failure_manifest, build_result_summary


RESULT_BUNDLE_SCHEMA = "paperbanana.result_bundle"
RESULT_BUNDLE_VERSION = 1


def companion_bundle_path(path: str | Path) -> Path:
    base_path = Path(path)
    if base_path.suffix:
        return base_path.with_suffix(".bundle.json")
    return Path(f"{base_path}.bundle.json")


def _sanitize_json_text(payload: Any) -> str:
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    return json_text.encode("utf-8", "ignore").decode("utf-8")


def write_json_payload(path: str | Path, payload: Any) -> Path:
    output_path = Path(path)
    output_path.write_text(_sanitize_json_text(payload), encoding="utf-8")
    return output_path


async def write_json_payload_async(path: str | Path, payload: Any) -> Path:
    output_path = Path(path)
    async with aiofiles.open(
        output_path,
        "w",
        encoding="utf-8",
        errors="surrogateescape",
    ) as f:
        await f.write(_sanitize_json_text(payload))
    return output_path


def _first_non_empty(mapping_list: list[dict[str, Any]], key: str) -> Any:
    for mapping in mapping_list:
        if not isinstance(mapping, dict):
            continue
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def build_run_manifest(
    *,
    exp_config: Any | None = None,
    producer: str,
    result_count: int = 0,
    created_at: str | None = None,
    extra: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    manifest = {
        "schema": RESULT_BUNDLE_SCHEMA,
        "schema_version": RESULT_BUNDLE_VERSION,
        "producer": producer,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "dataset_name": DEFAULT_DATASET_NAME,
        "task_name": "diagram",
        "split_name": "",
        "exp_mode": "",
        "exp_name": "",
        "timestamp": "",
        "timezone": "",
        "retrieval_setting": "",
        "provider": "",
        "model_name": "",
        "image_model_name": "",
        "concurrency_mode": "",
        "max_concurrent": 0,
        "max_critic_rounds": 0,
        "result_count": int(result_count or 0),
    }

    if exp_config is not None:
        manifest.update(
            {
                "dataset_name": normalize_dataset_name(
                    getattr(exp_config, "dataset_name", DEFAULT_DATASET_NAME)
                ),
                "task_name": normalize_task_name(
                    getattr(exp_config, "task_name", "diagram")
                ),
                "split_name": str(getattr(exp_config, "split_name", "") or ""),
                "exp_mode": str(getattr(exp_config, "exp_mode", "") or ""),
                "exp_name": str(getattr(exp_config, "exp_name", "") or ""),
                "timestamp": str(getattr(exp_config, "timestamp", "") or ""),
                "timezone": str(getattr(exp_config, "timezone", "") or ""),
                "retrieval_setting": str(
                    getattr(exp_config, "retrieval_setting", "") or ""
                ),
                "provider": str(getattr(exp_config, "provider", "") or ""),
                "model_name": str(getattr(exp_config, "model_name", "") or ""),
                "image_model_name": str(
                    getattr(exp_config, "image_model_name", "") or ""
                ),
                "concurrency_mode": str(
                    getattr(exp_config, "concurrency_mode", "") or ""
                ),
                "max_concurrent": int(getattr(exp_config, "max_concurrent", 0) or 0),
                "max_critic_rounds": int(
                    getattr(exp_config, "max_critic_rounds", 0) or 0
                ),
            }
        )

    manifest.update({key: value for key, value in overrides.items() if value is not None})
    manifest["dataset_name"] = normalize_dataset_name(
        manifest.get("dataset_name"),
        default=DEFAULT_DATASET_NAME,
    )
    manifest["task_name"] = normalize_task_name(manifest.get("task_name", "diagram"))
    manifest["result_count"] = int(manifest.get("result_count", result_count) or 0)
    manifest["max_concurrent"] = int(manifest.get("max_concurrent", 0) or 0)
    manifest["max_critic_rounds"] = int(manifest.get("max_critic_rounds", 0) or 0)
    if extra:
        manifest.update(extra)
    return manifest


def infer_manifest_from_results(
    results: list[dict[str, Any]],
    *,
    source_path: str | Path | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_sources: list[dict[str, Any]] = []
    if isinstance(raw_payload, dict):
        candidate_sources.append(raw_payload)
    candidate_sources.extend(item for item in results if isinstance(item, dict))

    dataset_name = _first_non_empty(candidate_sources, "dataset_name") or DEFAULT_DATASET_NAME
    task_name = _first_non_empty(candidate_sources, "task_name") or detect_task_type_from_result(results)

    manifest = build_run_manifest(
        producer=str(_first_non_empty(candidate_sources, "producer") or "legacy_file"),
        result_count=len(results),
        created_at=_first_non_empty(candidate_sources, "created_at"),
        dataset_name=dataset_name,
        task_name=task_name,
        split_name=_first_non_empty(candidate_sources, "split_name") or "",
        exp_mode=_first_non_empty(candidate_sources, "exp_mode") or "",
        exp_name=_first_non_empty(candidate_sources, "exp_name") or "",
        timestamp=_first_non_empty(candidate_sources, "timestamp") or "",
        timezone=_first_non_empty(candidate_sources, "timezone") or "",
        retrieval_setting=_first_non_empty(candidate_sources, "retrieval_setting") or "",
        provider=_first_non_empty(candidate_sources, "provider") or "",
        model_name=_first_non_empty(candidate_sources, "model_name") or "",
        image_model_name=_first_non_empty(candidate_sources, "image_model_name") or "",
        concurrency_mode=_first_non_empty(candidate_sources, "concurrency_mode") or "",
        max_concurrent=int(_first_non_empty(candidate_sources, "max_concurrent") or 0),
        max_critic_rounds=int(_first_non_empty(candidate_sources, "max_critic_rounds") or 0),
    )
    if source_path:
        manifest["source_file"] = Path(source_path).name
    return manifest


def _merge_manifest(
    preferred: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(fallback or {})
    for key, value in (preferred or {}).items():
        if value not in (None, "", [], {}):
            merged[key] = value
    merged["schema"] = RESULT_BUNDLE_SCHEMA
    merged["schema_version"] = RESULT_BUNDLE_VERSION
    merged["dataset_name"] = normalize_dataset_name(
        merged.get("dataset_name"),
        default=DEFAULT_DATASET_NAME,
    )
    merged["task_name"] = normalize_task_name(merged.get("task_name", "diagram"))
    merged["result_count"] = int(merged.get("result_count", 0) or 0)
    merged["max_concurrent"] = int(merged.get("max_concurrent", 0) or 0)
    merged["max_critic_rounds"] = int(merged.get("max_critic_rounds", 0) or 0)
    return merged


def build_result_bundle(
    results: list[dict[str, Any]],
    *,
    manifest: dict[str, Any],
    summary: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_results = list(results or [])
    inferred_manifest = infer_manifest_from_results(normalized_results)
    normalized_manifest = _merge_manifest(
        manifest,
        {
            **inferred_manifest,
            "result_count": len(normalized_results),
        },
    )
    normalized_manifest["result_count"] = len(normalized_results)
    return {
        "schema": RESULT_BUNDLE_SCHEMA,
        "schema_version": RESULT_BUNDLE_VERSION,
        "manifest": normalized_manifest,
        "summary": summary if isinstance(summary, dict) else build_result_summary(normalized_results),
        "failures": failures if isinstance(failures, list) else build_failure_manifest(normalized_results),
        "results": normalized_results,
    }


def write_result_bundle(
    path: str | Path,
    results: list[dict[str, Any]],
    *,
    manifest: dict[str, Any],
    summary: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> Path:
    bundle = build_result_bundle(
        results,
        manifest=manifest,
        summary=summary,
        failures=failures,
    )
    return write_json_payload(path, bundle)


async def write_result_bundle_async(
    path: str | Path,
    results: list[dict[str, Any]],
    *,
    manifest: dict[str, Any],
    summary: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> Path:
    bundle = build_result_bundle(
        results,
        manifest=manifest,
        summary=summary,
        failures=failures,
    )
    return await write_json_payload_async(path, bundle)


def _parse_jsonl_text(content: str) -> list[dict[str, Any]]:
    rows = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid JSONL at line {line_number}: each line must decode to an object."
            )
        rows.append(payload)
    return rows


def normalize_result_bundle_payload(
    payload: Any,
    *,
    source_path: str | Path | None = None,
) -> dict[str, Any]:
    if isinstance(payload, list):
        if any(not isinstance(item, dict) for item in payload):
            raise ValueError("Result arrays must contain only JSON objects.")
        manifest = infer_manifest_from_results(payload, source_path=source_path)
        return build_result_bundle(payload, manifest=manifest)

    if isinstance(payload, dict):
        results = payload.get("results")
        if not isinstance(results, list):
            raise ValueError(
                "Result files must be a JSON array, JSONL file, or JSON object with a 'results' array."
            )
        if any(not isinstance(item, dict) for item in results):
            raise ValueError("Bundle 'results' must contain only JSON objects.")
        inferred_manifest = infer_manifest_from_results(
            results,
            source_path=source_path,
            raw_payload=payload,
        )
        manifest = _merge_manifest(payload.get("manifest"), inferred_manifest)
        return build_result_bundle(
            results,
            manifest=manifest,
            summary=payload.get("summary"),
            failures=payload.get("failures"),
        )

    raise ValueError("Unsupported result payload type.")


def load_result_bundle(path: str | Path) -> dict[str, Any]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    content = input_path.read_text(encoding="utf-8").strip()
    if not content:
        return build_result_bundle(
            [],
            manifest=infer_manifest_from_results([], source_path=input_path),
        )

    payload: Any
    if input_path.suffix.lower() == ".jsonl":
        payload = _parse_jsonl_text(content)
    else:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = _parse_jsonl_text(content)

    return normalize_result_bundle_payload(payload, source_path=input_path)
