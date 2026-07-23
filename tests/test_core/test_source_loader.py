"""Source loading tests that do not require PyMuPDF."""

from __future__ import annotations

from pathlib import Path

from paperbanana_cn.core.source_loader import load_methodology_source


def test_load_methodology_source_txt_utf8_non_ascii(tmp_path: Path) -> None:
    """Regression test for #77: non-ASCII input must decode as UTF-8 regardless of locale.

    On Windows with a CJK locale the default codec is GBK; reading UTF-8 files
    without an explicit encoding raises UnicodeDecodeError. Write raw UTF-8
    bytes (independent of any platform default) and round-trip them through
    the methodology input loader used by `paperbanana generate --input`.
    """
    text = "稀疏路由的编码器-解码器架构概述 — naïve baseline 🍌"
    p = tmp_path / "methodology.txt"
    p.write_bytes(text.encode("utf-8"))
    assert load_methodology_source(p) == text
