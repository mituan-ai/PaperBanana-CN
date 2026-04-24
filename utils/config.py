# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for experiments."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Literal

from utils.retrieval_settings import (
    DEFAULT_CURATED_PROFILE,
    normalize_curated_profile_name,
    normalize_retrieval_setting,
)
from utils.runtime_settings import DEFAULT_PROVIDER, RuntimeSettings, resolve_runtime_settings

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # Python < 3.9 fallback


def sanitize_run_name_part(
    value: str | None,
    *,
    default: str,
    max_length: int = 24,
) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if not text:
        text = default
    return text[:max_length]


def build_run_name(
    *,
    timestamp: str,
    provider: str,
    model_name: str,
    image_model_name: str,
    retrieval_setting: str,
    curated_profile: str = DEFAULT_CURATED_PROFILE,
    exp_mode: str,
    split_name: str,
) -> str:
    provider_tag = sanitize_run_name_part(provider, default="provider", max_length=12)
    primary_model = image_model_name or model_name
    model_tag = sanitize_run_name_part(primary_model, default="model", max_length=24)
    normalized_retrieval = normalize_retrieval_setting(retrieval_setting)
    retrieval_tag = sanitize_run_name_part(
        f"{normalized_retrieval}ret",
        default="ret",
        max_length=16,
    )
    if normalized_retrieval == "curated":
        profile_tag = sanitize_run_name_part(
            normalize_curated_profile_name(curated_profile),
            default=DEFAULT_CURATED_PROFILE,
            max_length=16,
        )
        retrieval_tag = sanitize_run_name_part(
            f"{normalized_retrieval}-{profile_tag}ret",
            default="ret",
            max_length=20,
        )
    mode_tag = sanitize_run_name_part(exp_mode, default="mode", max_length=24)
    split_tag = sanitize_run_name_part(split_name, default="split", max_length=16)
    return f"{timestamp}_{provider_tag}_{model_tag}_{retrieval_tag}_{mode_tag}_{split_tag}"


@dataclass
class ExpConfig:
    """Experiment configuration"""

    dataset_name: str
    task_name: Literal["diagram", "plot"] = "diagram"
    split_name: str = "test"
    temperature: float = 1.0
    exp_mode: str = ""
    retrieval_setting: Literal["auto", "auto-full", "curated", "manual", "random", "none"] = "auto"
    curated_profile: str = DEFAULT_CURATED_PROFILE
    max_critic_rounds: int = 3
    concurrency_mode: Literal["auto", "manual"] = "auto"
    max_concurrent: int = 20
    model_name: str = ""
    image_model_name: str = ""
    provider: str = DEFAULT_PROVIDER
    connection_id: str = ""
    provider_display_name: str = ""
    image_provider: str = ""
    image_connection_id: str = ""
    image_provider_display_name: str = ""
    work_dir: Path = Path(__file__).parent.parent
    timezone: str = "America/Los_Angeles"

    timestamp: str | None = None
    runtime_settings: RuntimeSettings = field(init=False)

    def __post_init__(self):
        self.runtime_settings = resolve_runtime_settings(
            self.provider,
            connection_id=self.connection_id,
            model_name=self.model_name,
            image_model_name=self.image_model_name,
            image_connection_id=self.image_connection_id,
            concurrency_mode=self.concurrency_mode,
            max_concurrent=self.max_concurrent,
            max_critic_rounds=self.max_critic_rounds,
            base_dir=self.work_dir,
        )
        self.connection_id = self.runtime_settings.connection_id
        self.provider = self.runtime_settings.provider
        self.provider_display_name = self.runtime_settings.provider_display_name
        self.model_name = self.runtime_settings.model_name
        self.image_model_name = self.runtime_settings.image_model_name
        self.image_provider = self.runtime_settings.image_provider or self.runtime_settings.provider
        self.image_connection_id = self.runtime_settings.image_connection_id or self.runtime_settings.connection_id
        self.image_provider_display_name = (
            self.runtime_settings.image_provider_display_name
            or self.runtime_settings.provider_display_name
        )
        self.concurrency_mode = self.runtime_settings.concurrency_mode
        self.max_concurrent = self.runtime_settings.max_concurrent
        self.max_critic_rounds = self.runtime_settings.max_critic_rounds
        self.retrieval_setting = normalize_retrieval_setting(self.retrieval_setting)
        self.curated_profile = normalize_curated_profile_name(self.curated_profile)

        if self.timestamp is None:
            tz = ZoneInfo(self.timezone)
            self.timestamp = datetime.now(tz).strftime("%m%d_%H%M%S")

        self.exp_name = build_run_name(
            timestamp=self.timestamp,
            provider=self.connection_id or self.provider,
            model_name=self.model_name,
            image_model_name=self.image_model_name,
            retrieval_setting=self.retrieval_setting,
            curated_profile=self.curated_profile,
            exp_mode=self.exp_mode,
            split_name=self.split_name,
        )

        # mkdir result_dir if not exists
        self.result_dir = self.work_dir / "results" / f"{self.dataset_name}_{self.task_name}"
        self.result_dir.mkdir(exist_ok=True, parents=True)
