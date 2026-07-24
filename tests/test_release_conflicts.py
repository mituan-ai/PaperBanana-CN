"""Release conflict checks compare exact artifact and manifest content."""

from __future__ import annotations

import hashlib

from scripts.verify_pypi_release import local_hashes


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
