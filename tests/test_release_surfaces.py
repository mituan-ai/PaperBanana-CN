"""Regression tests for public release documentation and integrations."""

from __future__ import annotations

import json

import nbformat
from nbformat.validator import validate

from scripts.check_readme_release import ROOT, project_version, validate_readme


def test_bilingual_readmes_and_visual_assets_are_release_ready():
    version = project_version()
    errors: list[str] = []
    for name in ("README.md", "README_CN.md"):
        errors.extend(validate_readme(ROOT / name, version))
    assert errors == []


def test_colab_quickstart_is_clean_and_uses_the_release_identity():
    path = ROOT / "notebooks" / "PaperBanana_CN_Quickstart.ipynb"
    notebook = nbformat.read(path, as_version=4)
    validate(notebook)

    code = "\n".join(
        "".join(cell["source"]) for cell in notebook.cells if cell["cell_type"] == "code"
    )
    assert "paperbanana-cn==2.0.1" in code
    assert "paperbanana-cn connections add" in code
    assert "paperbanana-cn generate" in code
    assert "paperbanana " not in code
    code_cells = [cell for cell in notebook.cells if cell["cell_type"] == "code"]
    assert all(cell.get("execution_count") is None for cell in code_cells)
    assert all(cell.get("outputs", []) == [] for cell in code_cells)
    assert "github_pat_" not in json.dumps(notebook)


def test_dockerfile_uses_the_unique_command_and_non_root_user():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["paperbanana-cn"]' in dockerfile
    assert "USER paperbanana" in dockerfile
    assert "paperbanana-mcp" not in dockerfile
    assert "COPY paperbanana/" not in dockerfile
