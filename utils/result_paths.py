"""Shared helpers for resolving result-linked local assets."""

from __future__ import annotations

import os

from utils.dataset_paths import resolve_data_asset_path


def resolve_gt_image_path(
    raw_path: str | None,
    task_type: str,
    results_path: str | None = None,
    work_dir: str | os.PathLike[str] | None = None,
    dataset_name: str | None = None,
):
    return resolve_data_asset_path(
        raw_path,
        task_type,
        dataset_name=dataset_name,
        results_path=results_path,
        work_dir=work_dir if work_dir is not None else os.getcwd(),
    )
