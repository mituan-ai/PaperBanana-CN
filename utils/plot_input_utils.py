"""Helpers for parsing and previewing structured plot inputs."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any


def _normalize_scalar(value: str) -> Any:
    text = value.strip()
    if text == "":
        return ""
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "nan"}:
        return None
    try:
        if re.fullmatch(r"[+-]?\d+", text):
            return int(text)
        if re.fullmatch(r"[+-]?\d*\.\d+(e[+-]?\d+)?", text, flags=re.IGNORECASE) or re.fullmatch(
            r"[+-]?\d+e[+-]?\d+",
            text,
            flags=re.IGNORECASE,
        ):
            return float(text)
    except ValueError:
        return text
    return text


def _preview_from_records(records: list[dict[str, Any]], limit: int = 8) -> dict[str, Any]:
    if not records:
        return {
            "preview_rows": [],
            "columns": [],
            "row_count": 0,
        }
    columns = []
    for row in records:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key not in columns:
                columns.append(key)
    return {
        "preview_rows": records[:limit],
        "columns": columns,
        "row_count": len(records),
    }


def _parse_json_payload(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return {
                "format": "json",
                "normalized_content": payload,
                **_preview_from_records(payload),
            }
        return {
            "format": "json",
            "normalized_content": payload,
            "preview_rows": payload[:8],
            "columns": [],
            "row_count": len(payload),
        }
    if isinstance(payload, dict):
        return {
            "format": "json",
            "normalized_content": payload,
            "preview_rows": [payload],
            "columns": list(payload.keys()),
            "row_count": 1,
        }
    return {
        "format": "json",
        "normalized_content": payload,
        "preview_rows": [payload],
        "columns": [],
        "row_count": 1,
    }


def _parse_csv_payload(text: str) -> dict[str, Any] | None:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or "," not in lines[0]:
        return None
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if not reader.fieldnames:
        return None
    records = []
    for row in reader:
        if row is None:
            continue
        records.append({key: _normalize_scalar(value or "") for key, value in row.items()})
    if not records:
        return None
    return {
        "format": "csv",
        "normalized_content": records,
        **_preview_from_records(records),
    }


def _parse_markdown_table(text: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return None
    if "|" not in lines[0] or "|" not in lines[1]:
        return None

    header_parts = [part.strip() for part in lines[0].strip("|").split("|")]
    separator_parts = [part.strip() for part in lines[1].strip("|").split("|")]
    if len(header_parts) < 2 or len(separator_parts) != len(header_parts):
        return None
    if not all(re.fullmatch(r":?-{3,}:?", item) for item in separator_parts):
        return None

    records = []
    for raw_line in lines[2:]:
        row_parts = [part.strip() for part in raw_line.strip("|").split("|")]
        if len(row_parts) != len(header_parts):
            return None
        records.append(
            {
                header_parts[idx]: _normalize_scalar(row_parts[idx])
                for idx in range(len(header_parts))
            }
        )
    if not records:
        return None
    return {
        "format": "markdown_table",
        "normalized_content": records,
        **_preview_from_records(records),
    }


def parse_plot_input_text(text: str) -> dict[str, Any]:
    raw_text = str(text or "").strip()
    if not raw_text:
        return {
            "ok": False,
            "format": "empty",
            "normalized_content": "",
            "preview_rows": [],
            "columns": [],
            "row_count": 0,
            "error": "请输入 JSON、CSV 或 Markdown 表格格式的原始数据。",
        }

    for parser in (_parse_json_payload, _parse_markdown_table, _parse_csv_payload):
        parsed = parser(raw_text)
        if parsed is not None:
            return {
                "ok": True,
                **parsed,
                "error": "",
            }

    return {
        "ok": False,
        "format": "raw_text",
        "normalized_content": raw_text,
        "preview_rows": [],
        "columns": [],
        "row_count": 0,
        "error": "未能解析为 JSON、CSV 或 Markdown 表格。请检查格式，或显式选择按原始文本继续。",
    }
