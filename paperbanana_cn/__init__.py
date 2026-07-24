"""PaperBanana: Agentic framework for automated academic illustration generation."""

import sys

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

__version__ = "2.0.1"

from paperbanana_cn.core.pipeline import PaperBananaPipeline
from paperbanana_cn.core.types import DiagramType, GenerationInput, GenerationOutput

__all__ = [
    "PaperBananaPipeline",
    "DiagramType",
    "GenerationInput",
    "GenerationOutput",
]
