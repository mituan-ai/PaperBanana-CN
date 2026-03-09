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
        "auto": "auto — LLM 智能选参考，轻量模式",
        "auto-full": "auto-full — LLM 智能选参考，完整上下文",
        "curated": "curated — 固定 few-shot profile（兼容旧 manual）",
        "random": "random — 随机选 10 个参考（免费）",
        "none": "none — 不检索参考（免费）",
    }
    return labels[normalized]

