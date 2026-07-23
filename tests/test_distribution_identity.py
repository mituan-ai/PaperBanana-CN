"""Distribution identity and namespace regression tests."""

from __future__ import annotations

import ast
import configparser
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import tomllib

import paperbanana_cn
from paperbanana_cn.providers.image_gen.openrouter_imagen import OpenRouterImageGen
from paperbanana_cn.providers.vlm.openrouter import OpenRouterVLM

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPOSITORY = "https://github.com/llmsresearch/paperbanana"
UPSTREAM_ATTRIBUTION_ALLOWLIST = {
    "CONTRIBUTING.md",
    "README.md",
    "README_CN.md",
    "paperbanana_cn/data/manager.py",
}
PUBLIC_COMMAND_DOCS = [
    ROOT / "README.md",
    ROOT / "README_CN.md",
    ROOT / "mcp_server" / "README.md",
    ROOT / "docs" / "CONNECTIONS.md",
    ROOT / "docs" / "releases" / "v2.0.1.md",
    ROOT / "integrations" / "github-action" / "README.md",
]
PUBLISHED_IDENTITY_ROOTS = [
    ROOT / ".github",
    ROOT / "CONTRIBUTING.md",
    ROOT / "Dockerfile",
    ROOT / "README.md",
    ROOT / "README_CN.md",
    ROOT / "SECURITY.md",
    ROOT / "docs",
    ROOT / "integrations",
    ROOT / "mcp_server",
    ROOT / "notebooks",
    ROOT / "paperbanana_cn",
    ROOT / "pyproject.toml",
    ROOT / "scripts",
    ROOT / "server.json",
]


def _project_metadata() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]


def test_distribution_module_and_version_are_consistent():
    project = _project_metadata()

    assert project["name"] == "paperbanana-cn"
    assert project["version"] == "2.0.1"
    assert paperbanana_cn.__version__ == project["version"]
    assert project["scripts"] == {"paperbanana-cn": "paperbanana_cn.cli:app"}


def test_python_sources_do_not_import_removed_namespace():
    offenders: list[str] = []
    roots = [ROOT / "paperbanana_cn", ROOT / "mcp_server", ROOT / "scripts", ROOT / "tests"]
    for source_root in roots:
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                if any(name == "paperbanana" or name.startswith("paperbanana.") for name in names):
                    offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_upstream_repository_only_appears_in_attribution_and_dataset_sources():
    suffixes = {"", ".ipynb", ".json", ".md", ".py", ".toml", ".yaml", ".yml"}
    offenders: set[str] = set()
    for identity_root in PUBLISHED_IDENTITY_ROOTS:
        paths = [identity_root] if identity_root.is_file() else identity_root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if UPSTREAM_REPOSITORY in path.read_text(encoding="utf-8"):
                offenders.add(path.relative_to(ROOT).as_posix())

    assert offenders == UPSTREAM_ATTRIBUTION_ALLOWLIST


def test_public_docs_only_advertise_the_paperbanana_cn_command():
    old_command = re.compile(
        r"(?<![\w-])paperbanana(?:-mcp|\s+(?:connections|doctor|generate|mcp|plot|studio))\b"
    )
    offenders: list[str] = []
    for path in PUBLIC_COMMAND_DOCS:
        if old_command.search(path.read_text(encoding="utf-8")):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_readme_declares_mcp_registry_ownership():
    marker = "<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->"

    assert marker in (ROOT / "README.md").read_text(encoding="utf-8")


async def test_openrouter_requests_identify_paperbanana_cn():
    providers = [
        OpenRouterVLM(api_key="test-key"),
        OpenRouterImageGen(api_key="test-key"),
    ]

    try:
        for provider in providers:
            client = provider._get_client()
            assert client.headers["HTTP-Referer"] == ("https://github.com/mituan-ai/PaperBanana-CN")
            assert client.headers["X-Title"] == "PaperBanana-CN"
    finally:
        for provider in providers:
            if provider._client is not None:
                await provider._client.aclose()


def test_built_wheel_contains_only_new_namespace_and_command(tmp_path):
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
            str(ROOT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(tmp_path.glob("paperbanana_cn-2.0.1-*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        assert "paperbanana_cn/__init__.py" in names
        assert not any(name.startswith("paperbanana/") for name in names)
        entry_points_name = next(
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        )
        parser = configparser.ConfigParser()
        parser.read_string(archive.read(entry_points_name).decode("utf-8"))

    assert dict(parser["console_scripts"]) == {
        "paperbanana-cn": "paperbanana_cn.cli:app",
    }
