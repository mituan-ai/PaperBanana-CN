"""Structural gates for the required CI and multi-channel release workflows."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_workflow(name: str) -> tuple[dict, str]:
    path = ROOT / ".github" / "workflows" / name
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text), text


def test_ci_exposes_one_stable_required_gate():
    workflow, text = load_workflow("ci.yml")
    jobs = workflow["jobs"]

    assert {"release-surfaces", "action-smoke", "ci-success"} <= jobs.keys()
    assert set(jobs["ci-success"]["needs"]) == {
        "lint",
        "test",
        "studio-e2e",
        "build",
        "release-surfaces",
        "action-smoke",
    }
    assert jobs["ci-success"]["name"] == "ci-success"
    assert "python scripts/check_distribution_archive.py --dist-dir dist" in text
    assert "uses: ./integrations/github-action" in text
    assert "PAPERBANANA_CN_COMMAND" in text
    assert 'commit: "false"' in text


def test_release_orders_publication_after_pypi_install_verification():
    workflow, text = load_workflow("release.yml")
    jobs = workflow["jobs"]

    assert jobs["publish-pypi"]["environment"] == "pypi"
    assert jobs["verify-pypi-install"]["needs"] == "publish-pypi"
    assert jobs["publish-mcp"]["needs"] == "verify-pypi-install"
    assert jobs["publish-docker"]["needs"] == "verify-pypi-install"
    assert set(jobs["github-release"]["needs"]) == {
        "publish-pypi",
        "verify-pypi-install",
        "publish-mcp",
        "publish-docker",
    }
    assert jobs["release-audit"]["needs"] == "github-release"
    assert "docs/releases/${GITHUB_REF_NAME}.md" in text


def test_release_verifies_archives_mcp_images_and_public_surfaces():
    _, text = load_workflow("release.yml")

    required_fragments = {
        "check_distribution_archive.py",
        "check_readme_release.py --online",
        "scripts/smoke_mcp.py",
        "linux/amd64,linux/arm64",
        "sbom: true",
        "provenance: mode=max",
        "https://spdx.dev/Document",
        "https://slsa.dev/provenance/",
        "docker logout ghcr.io",
        "verify_pypi_release.py",
        "verify_mcp_release.py",
        "type=raw,value=${{ github.ref_name }}",
        "SHA256SUMS",
    }
    missing = {fragment for fragment in required_fragments if fragment not in text}
    assert missing == set()
