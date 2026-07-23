"""Distribution identity and namespace regression tests."""

from __future__ import annotations

import ast
import configparser
import subprocess
import sys
import zipfile
from pathlib import Path

import tomllib

import paperbanana_cn
from paperbanana_cn.providers.image_gen.openrouter_imagen import OpenRouterImageGen
from paperbanana_cn.providers.vlm.openrouter import OpenRouterVLM

ROOT = Path(__file__).resolve().parents[1]


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
