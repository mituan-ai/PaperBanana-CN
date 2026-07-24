"""Release conflict checks compare exact artifact and manifest content."""

from __future__ import annotations

import hashlib

from scripts.verify_mcp_release import comparable_registry_metadata
from scripts.verify_pypi_release import local_hashes, write_publish_output


def test_local_hashes_include_wheel_and_sdist_only(tmp_path):
    wheel = tmp_path / "paperbanana_cn-2.0.1-py3-none-any.whl"
    sdist = tmp_path / "paperbanana_cn-2.0.1.tar.gz"
    ignored = tmp_path / "SHA256SUMS"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    ignored.write_text("not an artifact", encoding="utf-8")

    assert local_hashes(tmp_path) == {
        wheel.name: hashlib.sha256(b"wheel").hexdigest(),
        sdist.name: hashlib.sha256(b"sdist").hexdigest(),
    }


def test_publish_decision_is_visible_in_logs_and_step_output(tmp_path, monkeypatch, capsys):
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    write_publish_output(False)

    assert capsys.readouterr().out == "publish=false\n"
    assert output.read_text(encoding="utf-8") == "publish=false\n"


def test_mcp_registry_comparison_ignores_only_unreturned_tools():
    local = {
        "name": "io.github.mituan-ai/paperbanana-cn",
        "version": "2.0.1",
        "title": "PaperBanana-CN",
        "tools": [{"name": "generate_diagram"}],
    }
    registered = {
        "name": "io.github.mituan-ai/paperbanana-cn",
        "version": "2.0.1",
        "title": "PaperBanana-CN",
    }

    assert comparable_registry_metadata(local) == comparable_registry_metadata(registered)
    registered["title"] = "Different title"
    assert comparable_registry_metadata(local) != comparable_registry_metadata(registered)
