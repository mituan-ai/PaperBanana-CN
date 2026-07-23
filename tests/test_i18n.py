"""Locale catalog completeness and UI-language isolation."""

from __future__ import annotations

import json
from importlib.resources import files

import pytest

from paperbanana_cn.i18n import SUPPORTED_LOCALES, get_translator


def _catalog(locale: str) -> dict[str, str]:
    path = files("paperbanana_cn.i18n").joinpath("locales", f"{locale}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_locale_catalogs_have_identical_keys():
    catalogs = [_catalog(locale) for locale in SUPPORTED_LOCALES]
    assert set(catalogs[0]) == set(catalogs[1])
    assert all(value.strip() for catalog in catalogs for value in catalog.values())


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
def test_translator_formats_runtime_values(locale):
    t = get_translator(locale)
    assert "run-1" in t("run.complete", run_id="run-1")


def test_chinese_and_english_catalogs_are_distinct():
    assert get_translator("zh-CN")("button.generate_diagram") == "生成方法图"
    assert get_translator("en")("button.generate_diagram") == "Generate diagram"


def test_chinese_connection_copy_uses_plain_product_language():
    catalog = _catalog("zh-CN")
    assert catalog["connection.profile"] == "已保存连接"
    assert catalog["connection.name"] == "连接名称"
    assert all("档案" not in value for value in catalog.values())


def test_interface_locale_does_not_enter_runtime_settings():
    from paperbanana_cn.core.config import Settings

    assert "locale" not in Settings.model_fields


@pytest.mark.parametrize(
    ("locale", "caption"),
    [
        ("zh-CN", "English labels only"),
        ("en", "图中标签使用中文"),
    ],
)
def test_interface_locale_does_not_change_figure_language(locale, caption):
    from paperbanana_cn.core.types import GenerationInput

    _ = get_translator(locale)("app.title")
    request = GenerationInput(
        source_context="method context",
        communicative_intent=caption,
    )
    assert request.communicative_intent == caption


def test_connection_setup_error_is_actionable_in_chinese():
    from paperbanana_cn.i18n import localize_error

    message = localize_error(
        ValueError("Active image and vlm connection profile(s) are required."),
        get_translator("zh-CN"),
    )
    assert "VLM" in message
    assert "连接" in message
