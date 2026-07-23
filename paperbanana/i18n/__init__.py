"""Locale catalogs for PaperBanana-CN user interfaces."""

from paperbanana.i18n.errors import localize_error
from paperbanana.i18n.translator import SUPPORTED_LOCALES, Translator, get_catalogs, get_translator

__all__ = [
    "SUPPORTED_LOCALES",
    "Translator",
    "get_catalogs",
    "get_translator",
    "localize_error",
]
