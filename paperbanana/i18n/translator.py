"""Small, strict JSON-catalog translator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

SUPPORTED_LOCALES = ("zh-CN", "en")


@dataclass(frozen=True)
class Translator:
    locale: str
    catalog: dict[str, str]

    def __call__(self, key: str, **values: object) -> str:
        try:
            text = self.catalog[key]
        except KeyError as exc:
            raise KeyError(f"Missing i18n key '{key}' for locale {self.locale}") from exc
        return text.format(**values) if values else text


def get_translator(locale: str = "zh-CN") -> Translator:
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale: {locale}")
    path = files("paperbanana.i18n").joinpath("locales", f"{locale}.json")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    return Translator(locale=locale, catalog=catalog)


def get_catalogs() -> dict[str, dict[str, str]]:
    """Return locale catalogs in the shape expected by Gradio's frontend i18n."""
    return {locale: get_translator(locale).catalog for locale in SUPPORTED_LOCALES}
