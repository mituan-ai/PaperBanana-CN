"""Shared retrieval-setting helpers."""

from __future__ import annotations

import re


DEFAULT_CURATED_PROFILE = "default"
CANONICAL_RETRIEVAL_SETTINGS = (
    "auto",
    "auto-full",
    "curated",
    "random",
    "none",
)
RETRIEVAL_SETTING_ALIASES = {
    "manual": "curated",
}
CLI_RETRIEVAL_SETTING_CHOICES = (
    "auto",
    "auto-full",
    "curated",
    "manual",
    "random",
    "none",
)


def normalize_retrieval_setting(value: str | None, *, default: str = "auto") -> str:
    normalized = str(value or "").strip().lower()
    normalized = RETRIEVAL_SETTING_ALIASES.get(normalized, normalized)
    if normalized in CANONICAL_RETRIEVAL_SETTINGS:
        return normalized
    return default


def normalize_curated_profile_name(
    profile_name: str | None,
    *,
    default: str = DEFAULT_CURATED_PROFILE,
) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(profile_name or "").strip()).strip("-")
    return normalized or default


def get_retrieval_setting_label(value: str) -> str:
    normalized = normalize_retrieval_setting(value)
    labels = {
        "auto": "智能检索（轻量）",
        "auto-full": "智能检索（高精度）",
        "curated": "固定参考集",
        "random": "随机参考样本",
        "none": "不使用参考",
    }
    return labels[normalized]
