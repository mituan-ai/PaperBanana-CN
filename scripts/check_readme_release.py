#!/usr/bin/env python3
"""Validate README assets, product links, and the live PyPI release surface."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple

from PIL import Image

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
RAW_PREFIX = "https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/"
PYPI_PROJECT_URL = "https://pypi.org/project/paperbanana-cn/"
PYPI_JSON_URL = "https://pypi.org/pypi/paperbanana-cn/json"
MCP_MARKER = "<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->"
USER_AGENT = "PaperBanana-CN release audit"


class ImageRef(NamedTuple):
    src: str
    alt: str
    href: str | None


class ReadmeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_href: str | None = None
        self.images: list[ImageRef] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.current_href = values["href"]
            self.links.append(values["href"])
        elif tag == "img" and values.get("src"):
            self.images.append(ImageRef(values["src"], values.get("alt", ""), self.current_href))

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.current_href = None


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def parse_readme(path: Path) -> tuple[str, ReadmeHTMLParser]:
    text = path.read_text(encoding="utf-8")
    parser = ReadmeHTMLParser()
    parser.feed(text)
    return text, parser


def referenced_local_assets(parser: ReadmeHTMLParser) -> list[Path]:
    paths: list[Path] = []
    for image in parser.images:
        if image.src.startswith(RAW_PREFIX):
            paths.append(ROOT / image.src.removeprefix(RAW_PREFIX))
    return paths


def validate_raster(path: Path) -> list[str]:
    errors: list[str] = []
    with Image.open(path) as image:
        width, height = image.size
        if width < 300 or height < 180:
            errors.append(f"{path}: README raster is too small ({width}x{height})")
        if image.format == "GIF":
            if getattr(image, "n_frames", 1) < 3:
                errors.append(f"{path}: workflow GIF must contain multiple frames")
            if image.info.get("loop") != 0:
                errors.append(f"{path}: workflow GIF must loop indefinitely")
    if path.stat().st_size > 1_000_000:
        errors.append(f"{path}: README asset exceeds 1 MB")
    return errors


def validate_svg(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"{path}: invalid SVG XML: {exc}"]
    if root.tag.rsplit("}", 1)[-1] != "svg":
        errors.append(f"{path}: root element is not svg")
    if "viewBox" not in root.attrib:
        errors.append(f"{path}: SVG requires a viewBox")
    return errors


def validate_asset(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: referenced README asset does not exist"]
    if path.suffix.lower() == ".svg":
        return validate_svg(path)
    return validate_raster(path)


def validate_readme(path: Path, version: str) -> list[str]:
    text, parser = parse_readme(path)
    errors: list[str] = []
    if MCP_MARKER not in text:
        errors.append(f"{path}: missing MCP ownership marker")
    if "github_pat_" in text or "/home/zongyoucheng" in text:
        errors.append(f"{path}: contains a credential or local path")
    if "sealed_token=" not in text:
        errors.append(f"{path}: Star History sealed token is missing")

    public_urls = [
        url
        for url in [*parser.links, *(image.src for image in parser.images)]
        if url.startswith(("http://", "https://"))
    ]
    for url in public_urls:
        if not url.isascii():
            errors.append(f"{path}: public URL must be percent-encoded: {url}")

    pypi_images = [image for image in parser.images if image.href == PYPI_PROJECT_URL]
    if not pypi_images:
        errors.append(f"{path}: PyPI button is not linked to {PYPI_PROJECT_URL}")
    if not any("PYPI" in image.src.upper() for image in pypi_images):
        errors.append(f"{path}: PyPI link does not wrap a PyPI-labelled image")

    version_badges = [
        image.src
        for image in parser.images
        if "img.shields.io" in image.src
        and ("pypi/v/paperbanana-cn" in image.src or f"Package-{version}" in image.src)
    ]
    if not version_badges:
        errors.append(f"{path}: no package version badge matches {version}")

    required_fragments = [
        "actions/workflows/ci.yml",
        "mcp_server/README.md",
        "notebooks/PaperBanana_CN_Quickstart.ipynb",
        "/blob/main/LICENSE",
        "api.star-history.com/chart",
    ]
    for fragment in required_fragments:
        if fragment not in text:
            errors.append(f"{path}: missing required public link containing {fragment}")

    assets = referenced_local_assets(parser)
    asset_names = {asset.name for asset in assets}
    if not any(name.startswith("hero") for name in asset_names):
        errors.append(f"{path}: project hero is missing")
    if "studio-workflow.gif" not in asset_names:
        errors.append(f"{path}: real Studio workflow recording is missing")
    for asset in assets:
        errors.extend(validate_asset(asset))
    return errors


def request_url(url: str, *, attempts: int = 3) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read(256)
                return response.status, response.headers.get_content_type()
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def live_asset_urls() -> list[str]:
    urls: set[str] = set()
    for name in ("README.md", "README_CN.md"):
        _, parser = parse_readme(ROOT / name)
        urls.update(image.src for image in parser.images if image.src.startswith(RAW_PREFIX))
        urls.update(
            image.src
            for image in parser.images
            if image.href == PYPI_PROJECT_URL and "img.shields.io" in image.src
        )
    return sorted(urls)


def validate_live_release(version: str) -> list[str]:
    errors: list[str] = []
    try:
        with urllib.request.urlopen(
            urllib.request.Request(PYPI_JSON_URL, headers={"User-Agent": USER_AGENT}),
            timeout=30,
        ) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return [f"PyPI JSON is unavailable: {exc}"]

    info = payload.get("info", {})
    if info.get("name") != "paperbanana-cn":
        errors.append(f"PyPI project name mismatch: {info.get('name')!r}")
    if info.get("version") != version:
        errors.append(f"PyPI version mismatch: {info.get('version')!r} != {version!r}")
    project_urls = info.get("project_urls") or {}
    if project_urls.get("Homepage") != "https://github.com/mituan-ai/PaperBanana-CN":
        errors.append("PyPI Homepage does not point to PaperBanana-CN")

    urls = [PYPI_PROJECT_URL, *live_asset_urls()]
    for url in urls:
        try:
            status, content_type = request_url(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"{url}: unavailable after retries: {exc}")
            continue
        if status != 200:
            errors.append(f"{url}: returned HTTP {status}")
        if url.startswith(RAW_PREFIX) and not (
            content_type.startswith("image/") or content_type == "application/octet-stream"
        ):
            errors.append(f"{url}: unexpected content type {content_type}")
    return errors


def run_checks(*, online: bool) -> list[str]:
    version = project_version()
    errors: list[str] = []
    for name in ("README.md", "README_CN.md"):
        errors.extend(validate_readme(ROOT / name, version))
    if online:
        errors.extend(validate_live_release(version))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--online",
        action="store_true",
        help="Also require the published PyPI project, badges, and raw assets.",
    )
    args = parser.parse_args()
    errors = run_checks(online=args.online)
    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    mode = "local and online" if args.online else "local"
    print(f"README release audit passed ({mode}).")


if __name__ == "__main__":
    main()
