#!/usr/bin/env python3
"""Check that release archives contain only the PaperBanana-CN distribution."""

from __future__ import annotations

import argparse
import configparser
import io
import re
import tarfile
import zipfile
from pathlib import Path

FORBIDDEN_PARTS = {
    ".env",
    ".git",
    ".venv",
    "AGENTS.md",
    "PAPERBANANA_CN_REBUILD_PLAN.md",
    "outputs",
    "session_state.json",
}


def normalized_member(name: str) -> str:
    parts = name.split("/")
    if parts and re.fullmatch(r"paperbanana_cn-\d+\.\d+\.\d+", parts[0]):
        parts = parts[1:]
    return "/".join(parts)


def forbidden_members(names: list[str]) -> list[str]:
    offenders: list[str] = []
    for name in names:
        normalized = normalized_member(name)
        parts = set(Path(normalized).parts)
        if parts & FORBIDDEN_PARTS or normalized.startswith("paperbanana/"):
            offenders.append(name)
    return offenders


def check_wheel(path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        offenders = forbidden_members(names)
        if offenders:
            errors.append(f"{path}: forbidden members: {offenders}")
        if "paperbanana_cn/__init__.py" not in names:
            errors.append(f"{path}: paperbanana_cn namespace is missing")
        if any(name.startswith("paperbanana/") for name in names):
            errors.append(f"{path}: removed paperbanana namespace is present")
        entry_points = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_points) != 1:
            errors.append(f"{path}: expected one entry_points.txt")
        else:
            parser = configparser.ConfigParser()
            parser.read_string(archive.read(entry_points[0]).decode("utf-8"))
            scripts = dict(parser["console_scripts"])
            if scripts != {"paperbanana-cn": "paperbanana_cn.cli:app"}:
                errors.append(f"{path}: unexpected console scripts: {scripts}")
    return errors


def check_sdist(path: Path) -> list[str]:
    errors: list[str] = []
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        offenders = forbidden_members(names)
        if offenders:
            errors.append(f"{path}: forbidden members: {offenders}")
        pyproject_names = [name for name in names if name.endswith("/pyproject.toml")]
        if len(pyproject_names) != 1:
            errors.append(f"{path}: expected one pyproject.toml")
        else:
            member = archive.extractfile(pyproject_names[0])
            if member is None:
                errors.append(f"{path}: cannot read pyproject.toml")
            elif b'name = "paperbanana-cn"' not in io.BytesIO(member.read()).getvalue():
                errors.append(f"{path}: distribution name is incorrect")
    return errors


def validate_dist(dist_dir: Path) -> list[str]:
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    errors: list[str] = []
    if len(wheels) != 1:
        errors.append(f"{dist_dir}: expected one wheel, found {len(wheels)}")
    if len(sdists) != 1:
        errors.append(f"{dist_dir}: expected one sdist, found {len(sdists)}")
    for wheel in wheels:
        errors.extend(check_wheel(wheel))
    for sdist in sdists:
        errors.extend(check_sdist(sdist))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    errors = validate_dist(args.dist_dir)
    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    print("Wheel and sdist archive audit passed.")


if __name__ == "__main__":
    main()
