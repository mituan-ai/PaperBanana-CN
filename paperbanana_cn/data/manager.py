"""Dataset management — download and cache official PaperBananaBench reference sets.

Cache layout:
    ~/.cache/paperbanana-cn/              (or PAPERBANANA_CACHE_DIR)
    ├── reference_sets/
    │   ├── index.json
    │   ├── dataset_info.json          (version + revision tracking)
    │   └── images/
    │       ├── ref_001.jpg
    │       └── ...
    └── test_split/                    (official PaperBananaBench test split)
        ├── diagram/
        │   ├── test.json
        │   └── images/
        └── plot/
            ├── test.json
            └── images/
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import structlog

if TYPE_CHECKING:
    from paperbanana_cn.core.types import TestCase

logger = structlog.get_logger()

# Pinned archive published by the upstream PaperBanana project from
# https://huggingface.co/datasets/dwzhu/PaperBananaBench.
DATASET_RELEASE_TAG = "bench-data-v1"
DATASET_URL = (
    "https://github.com/llmsresearch/paperbanana/releases/download/"
    f"{DATASET_RELEASE_TAG}/PaperBananaBench.zip"
)
DATASET_SHA256 = "a980d23954c0cb47017cdaa8a9029dbea3598791fd269a457482033821927e37"
DATASET_VERSION = "1.0.0"


def default_cache_dir() -> Path:
    """Get the default cache directory using platformdirs."""
    from platformdirs import user_cache_dir

    return Path(user_cache_dir("paperbanana-cn"))


def resolve_cache_dir(override: Optional[str] = None) -> Path:
    """Resolve cache directory from override → env var → platformdirs default.

    Args:
        override: Explicit cache dir path (highest priority).

    Returns:
        Resolved cache directory path.
    """
    if override:
        return Path(override)
    env_dir = os.environ.get("PAPERBANANA_CACHE_DIR")
    if env_dir:
        return Path(env_dir)
    return default_cache_dir()


class DatasetManager:
    """Manages downloading and caching of the official PaperBananaBench dataset.

    Provides a clean API for:
    - Downloading the dataset from HuggingFace
    - Converting to PaperBanana's index.json format
    - Caching in a user-local directory (~/.cache/paperbanana-cn/)
    - Checking availability and version info
    """

    def __init__(self, cache_dir: Optional[str | Path] = None):
        """Initialize DatasetManager.

        Args:
            cache_dir: Override cache directory. Defaults to PAPERBANANA_CACHE_DIR
                       env var or ~/.cache/paperbanana-cn/.
        """
        self._cache_dir = resolve_cache_dir(str(cache_dir) if cache_dir else None)

    @property
    def cache_dir(self) -> Path:
        """Root cache directory."""
        return self._cache_dir

    @property
    def reference_dir(self) -> Path:
        """Directory containing expanded reference set."""
        return self._cache_dir / "reference_sets"

    @property
    def index_path(self) -> Path:
        """Path to reference set index.json in cache."""
        return self.reference_dir / "index.json"

    @property
    def info_path(self) -> Path:
        """Path to dataset version info."""
        return self.reference_dir / "dataset_info.json"

    @property
    def test_split_dir(self) -> Path:
        """Directory containing the cached official test split."""
        return self._cache_dir / "test_split"

    def test_split_index_path(self, task: str) -> Path:
        """Path to the cached, normalized test.json for a task."""
        return self.test_split_dir / task / "test.json"

    def is_test_split_downloaded(self, task: str) -> bool:
        """Check if the official test split for *task* is cached."""
        return self.test_split_index_path(task).exists()

    def is_downloaded(self) -> bool:
        """Check if an expanded reference set is available in cache.

        Note:
            Caches that pre-date ``dataset_info.json`` (only ``index.json``
            present) are treated as a downloaded expansion. Old-format
            ``dataset_info.json`` files (top-level ``source`` instead of a
            ``datasets`` list) are also honoured.
        """
        info = self.get_info()
        if info is None:
            # Legacy caches may only have index.json with no dataset_info.json.
            return self.index_path.exists()
        if info.get("datasets"):
            return True
        # Back-compat: old dataset_info.json without "datasets" key recorded a
        # top-level "source" instead.
        return bool(info.get("source"))

    def get_info(self) -> Optional[dict]:
        """Get cached dataset info (version, revision, count).

        Returns:
            Dataset info dict or None if not downloaded.
        """
        if not self.info_path.exists():
            return None
        try:
            with open(self.info_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def get_example_count(self) -> int:
        """Get the number of examples in the cached dataset."""
        if not self.index_path.exists():
            return 0
        try:
            with open(self.index_path, encoding="utf-8") as f:
                data = json.load(f)
            return len(data.get("examples", []))
        except (json.JSONDecodeError, OSError):
            return 0

    def download(
        self,
        *,
        task: str = "diagram",
        force: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """Download and cache the PaperBananaBench reference dataset.

        Fetches the project-controlled GitHub release mirror (~254 MB) and
        verifies its SHA256 checksum before extraction.

        Args:
            task: Which references to import ('diagram', 'plot', or 'both').
            force: Re-download even if already cached.
            progress_callback: Optional callback(message) for progress updates.

        Returns:
            Number of examples in the cache after import.

        Raises:
            RuntimeError: If download, checksum verification, or extraction
                fails.
        """
        if self.is_downloaded() and not force:
            count = self.get_example_count()
            logger.info("Dataset already cached", count=count, path=str(self.reference_dir))
            return count

        def _log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        with tempfile.TemporaryDirectory(prefix="paperbanana_") as tmp:
            tmp_dir = Path(tmp)
            zip_path = tmp_dir / "PaperBananaBench.zip"

            # Download
            _log(f"Downloading PaperBananaBench ({DATASET_RELEASE_TAG})...")
            _download_file(DATASET_URL, zip_path)

            # Verify integrity before touching the archive
            _log("Verifying checksum...")
            _verify_sha256(zip_path, DATASET_SHA256)

            # Extract
            _log("Extracting dataset...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp_dir)

            bench_dir = tmp_dir / "PaperBananaBench"
            if not bench_dir.exists():
                candidates = list(tmp_dir.glob("*/PaperBananaBench"))
                if candidates:
                    bench_dir = candidates[0]
                else:
                    raise RuntimeError(
                        "Could not find PaperBananaBench directory in extracted archive."
                    )

            # Convert and cache
            _log("Converting to PaperBanana format...")
            self.reference_dir.mkdir(parents=True, exist_ok=True)
            images_dir = self.reference_dir / "images"
            images_dir.mkdir(exist_ok=True)

            bench_examples = _import_from_bench(bench_dir, task, images_dir)
            count = _merge_index(self.index_path, bench_examples)

            # Cache the official test split alongside the reference import
            _log("Caching official test split...")
            test_count = _import_test_split(bench_dir, task, self.test_split_dir)

            # Update dataset_info.json
            self._record_dataset(
                "full_bench",
                DATASET_VERSION,
                DATASET_URL,
                count,
                extra={
                    "revision": DATASET_RELEASE_TAG,
                    "task": task,
                    "test_cases": test_count,
                },
            )

            _log(f"Cached {count} reference examples to {self.reference_dir}")
            if test_count:
                _log(f"Cached {test_count} official test cases to {self.test_split_dir}")
            return count

    def load_test_split(self, task: str = "diagram") -> list[TestCase]:
        """Load the official PaperBananaBench test split for a task.

        Args:
            task: Which split to load ('diagram' or 'plot').

        Returns:
            List of typed TestCase entries with absolute ground-truth image paths.

        Raises:
            ValueError: If *task* is not 'diagram' or 'plot'.
            RuntimeError: If the test split has not been downloaded yet.
        """
        from paperbanana_cn.core.types import TestCase

        if task not in ("diagram", "plot"):
            raise ValueError(f"task must be 'diagram' or 'plot', got: {task}")

        index_path = self.test_split_index_path(task)
        if not index_path.exists():
            raise RuntimeError(
                f"Official test split for task '{task}' not found at {index_path}. "
                "Run 'paperbanana-cn data download --force' to fetch and cache it."
            )

        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)

        task_dir = index_path.parent
        cases: list[TestCase] = []
        for raw in data.get("cases", []):
            raw = dict(raw)
            raw["gt_image_path"] = str(task_dir / raw.get("gt_image_path", ""))
            cases.append(TestCase(**raw))
        return cases

    def _record_dataset(
        self,
        dataset: str,
        version: str,
        source: str,
        example_count: int,
        extra: dict | None = None,
    ) -> None:
        """Update dataset_info.json, preserving the list of downloaded datasets."""
        info = self.get_info() or {}
        downloaded = set(info.get("datasets", []))
        # Back-compat: old dataset_info.json without "datasets" key recorded a
        # top-level "source" — written by the full_bench downloader.
        if not downloaded and info.get("source"):
            downloaded.add("full_bench")
        downloaded.add(dataset)

        dataset_meta: dict = info.get("dataset_meta", {})
        meta_entry: dict = {"version": version, "source": source}
        if extra:
            meta_entry.update(extra)
        dataset_meta[dataset] = meta_entry

        info.update(
            {
                "datasets": sorted(downloaded),
                "dataset_meta": dataset_meta,
                "example_count": example_count,
            }
        )
        info.pop("version", None)
        info.pop("source", None)
        info.pop("revision", None)

        with open(self.info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)

    def clear(self) -> None:
        """Remove cached dataset."""
        if self.reference_dir.exists():
            shutil.rmtree(self.reference_dir)
            logger.info("Cleared cached dataset", path=str(self.reference_dir))
        if self.test_split_dir.exists():
            shutil.rmtree(self.test_split_dir)
            logger.info("Cleared cached test split", path=str(self.test_split_dir))


def _download_file(url: str, dest: Path) -> None:
    """Download a file using httpx (already a project dependency)."""
    import httpx

    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)


def _verify_sha256(path: Path, expected: str) -> None:
    """Verify a file's SHA256 checksum, raising RuntimeError on mismatch."""
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"SHA256 mismatch for {path.name}: expected {expected}, got {actual}. "
            "The downloaded archive is corrupted or has been tampered with — aborting."
        )


def _merge_index(index_path: Path, new_examples: list[dict]) -> int:
    """Merge new examples into an existing cached index.json.

    Deduplicates by example ID — new entries overwrite existing ones with the
    same ID. Returns the total example count after merge.
    """
    existing_examples: list[dict] = []
    if index_path.exists():
        try:
            with open(index_path, encoding="utf-8") as f:
                data = json.load(f)
            existing_examples = data.get("examples", [])
        except (json.JSONDecodeError, OSError):
            pass

    by_id: dict[str, dict] = {}
    no_id: list[dict] = []
    for ex in existing_examples:
        ex_id = ex.get("id", "")
        if ex_id:
            by_id[ex_id] = ex
        else:
            no_id.append(ex)
    for ex in new_examples:
        ex_id = ex.get("id", "")
        if ex_id:
            by_id[ex_id] = ex
        else:
            no_id.append(ex)

    merged = list(by_id.values()) + no_id
    categories = sorted(set(e.get("category", "") for e in merged if e.get("category")))

    index_data = {
        "metadata": {
            "name": "paperbanana_combined",
            "description": (
                f"Combined reference set. "
                f"{len(merged)} examples across {len(categories)} categories."
            ),
            "version": "3.0.0",
            "categories": categories,
            "total_examples": len(merged),
        },
        "examples": merged,
    }

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    return len(merged)


def _resolve_image(source_images_dir: Path, gt_image_rel: str) -> Optional[Path]:
    """Resolve a dataset image path tolerantly across Unicode normalization forms.

    macOS extracts zip entries with NFD-normalized filenames, so a byte-exact
    lookup misses names containing characters like U+2011 (non-breaking hyphen)
    or U+200C (zero-width non-joiner). When the exact paths miss, fall back to
    an NFC-normalized filename comparison within the candidate directories.
    """
    candidates = [source_images_dir / gt_image_rel, source_images_dir.parent / gt_image_rel]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    want = unicodedata.normalize("NFC", Path(gt_image_rel).name)
    for candidate in candidates:
        parent = candidate.parent
        if not parent.is_dir():
            continue
        for f in parent.iterdir():
            if unicodedata.normalize("NFC", f.name) == want:
                return f
    return None


def _import_from_bench(
    bench_dir: Path,
    task: str,
    images_dir: Path,
) -> list[dict]:
    """Convert official dataset format to a list of example dicts.

    Images are copied into *images_dir*; the caller is responsible for
    merging the returned examples into the cached ``index.json`` (via
    ``_merge_index``) so that previously-cached entries are preserved.

    Args:
        bench_dir: Extracted PaperBananaBench directory.
        task: 'diagram', 'plot', or 'both'.
        images_dir: Destination directory for reference images.

    Returns:
        List of imported example dicts.
    """
    from PIL import Image

    tasks = ["diagram", "plot"] if task == "both" else [task]
    all_examples: list[dict] = []

    for t in tasks:
        task_dir = bench_dir / t
        ref_file = task_dir / "ref.json"

        if not ref_file.exists():
            logger.warning("Task ref.json not found, skipping", task=t, path=str(ref_file))
            continue

        with open(ref_file, encoding="utf-8") as f:
            entries = json.load(f)

        source_images_dir = task_dir / "images"
        count = 0

        for entry in entries:
            entry_id = entry.get("id", "")
            if task == "both":
                entry_id = f"{t}_{entry_id}"

            # Map fields from official → community format
            source_context = entry.get("content", "")
            if isinstance(source_context, (dict, list)):
                source_context = json.dumps(source_context, indent=2)

            example: dict = {
                "id": entry_id,
                "source_context": source_context,
                "caption": entry.get("visual_intent", ""),
                "category": entry.get("category", ""),
                "source_paper": entry_id,
            }

            # Copy image
            gt_image_rel = entry.get("path_to_gt_image", "")
            if not gt_image_rel:
                continue

            source_image = _resolve_image(source_images_dir, gt_image_rel)
            if source_image is None:
                logger.warning("Image not found, skipping", id=entry_id, path=gt_image_rel)
                continue

            dest_filename = f"{entry_id}.jpg"
            dest_image = images_dir / dest_filename
            if not dest_image.exists():
                shutil.copy2(source_image, dest_image)

            example["image_path"] = f"images/{dest_filename}"

            # Compute aspect ratio
            try:
                with Image.open(dest_image) as img:
                    w, h = img.size
                    example["aspect_ratio"] = round(w / h, 2) if h > 0 else None
            except Exception:
                example["aspect_ratio"] = None

            all_examples.append(example)
            count += 1

        logger.info("Imported task references", task=t, count=count, total=len(entries))

    if not all_examples:
        raise RuntimeError("No examples could be imported from the dataset.")

    return all_examples


def _import_test_split(
    bench_dir: Path,
    task: str,
    dest_root: Path,
) -> int:
    """Cache the official test split (test.json + images) in normalized form.

    Converts each upstream test entry to the TestCase schema and copies its
    ground-truth image into ``dest_root/<task>/images/<id><ext>`` (ID-based
    names sidestep Unicode-normalization issues in cached filenames). Writes
    ``dest_root/<task>/test.json`` per task.

    Args:
        bench_dir: Extracted PaperBananaBench directory.
        task: 'diagram', 'plot', or 'both'.
        dest_root: Destination root for the cached test split.

    Returns:
        Total number of imported test cases across tasks.
    """
    tasks = ["diagram", "plot"] if task == "both" else [task]
    total = 0

    for t in tasks:
        task_dir = bench_dir / t
        test_file = task_dir / "test.json"

        if not test_file.exists():
            logger.warning("Task test.json not found, skipping", task=t, path=str(test_file))
            continue

        with open(test_file, encoding="utf-8") as f:
            entries = json.load(f)

        source_images_dir = task_dir / "images"
        dest_dir = dest_root / t
        images_dir = dest_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        cases: list[dict] = []
        for entry in entries:
            entry_id = str(entry.get("id", ""))
            gt_image_rel = entry.get("path_to_gt_image", "")
            if not entry_id or not gt_image_rel:
                continue

            source_image = _resolve_image(source_images_dir, gt_image_rel)
            if source_image is None:
                logger.warning("Test image not found, skipping", id=entry_id, path=gt_image_rel)
                continue

            dest_filename = f"{entry_id}{source_image.suffix or '.jpg'}"
            dest_image = images_dir / dest_filename
            if not dest_image.exists():
                shutil.copy2(source_image, dest_image)

            content = entry.get("content", "")
            raw_data = content if isinstance(content, dict) else None
            if isinstance(content, (dict, list)):
                source_context = json.dumps(content, indent=2)
            else:
                source_context = content

            additional = entry.get("additional_info") or {}
            cases.append(
                {
                    "id": entry_id,
                    "task": t,
                    "category": entry.get("category", "") or "",
                    "source_context": source_context,
                    "caption": entry.get("visual_intent", ""),
                    "gt_image_path": f"images/{dest_filename}",
                    "aspect_ratio": additional.get("rounded_ratio"),
                    "raw_data": raw_data,
                    "gt_code": additional.get("gt_code"),
                    "difficulty": entry.get("difficulty"),
                }
            )

        index_data = {
            "metadata": {
                "name": f"paperbananabench_test_{t}",
                "description": f"Official PaperBananaBench {t} test split ({len(cases)} cases).",
                "task": t,
                "total_cases": len(cases),
            },
            "cases": cases,
        }
        with open(dest_dir / "test.json", "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        total += len(cases)
        logger.info("Imported test split", task=t, count=len(cases), total=len(entries))

    return total


def resolve_reference_path(
    settings_path: str,
    cache_dir: Optional[str] = None,
) -> str:
    """Resolve reference set path with fallback chain.

    Priority:
    1. Explicit settings path (non-default, from config/env/YAML)
    2. Cached expanded dataset (~/.cache/paperbanana-cn/reference_sets/)
    3. Built-in reference set (data/reference_sets/)

    Args:
        settings_path: The reference_set_path from Settings (may be default or user-set).
        cache_dir: Optional cache dir override.

    Returns:
        Resolved path to the reference set directory.
    """
    default_path = "data/reference_sets"

    # If settings_path differs from the default, the user explicitly configured it
    # (via env var REFERENCE_SET_PATH, YAML config, or CLI). Honor it unconditionally.
    if settings_path != default_path:
        logger.info("Using explicitly configured reference set", path=settings_path)
        return settings_path

    # Check if any expanded dataset is cached (uses dataset_info.json marker)
    manager = DatasetManager(cache_dir=cache_dir)
    if manager.is_downloaded():
        logger.info(
            "Using cached expanded reference set",
            path=str(manager.reference_dir),
            count=manager.get_example_count(),
        )
        return str(manager.reference_dir)

    # Fallback to built-in
    return settings_path
