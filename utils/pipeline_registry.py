"""Registry of supported pipeline modes and their stage layouts."""

from __future__ import annotations

from dataclasses import dataclass


RENDER_STAGE_SOURCES = ("vanilla", "planner", "stylist", "critic", "polish")


@dataclass(frozen=True)
class PipelineSpec:
    stages: tuple[str, ...]
    eval_image_source: str | None = None
    critic_source: str | None = None
    disable_eval: bool = False

    def render_stage_sources(self) -> tuple[str, ...]:
        return tuple(stage for stage in self.stages if stage in RENDER_STAGE_SOURCES)

    def base_render_source(self) -> str | None:
        non_critic_sources = [
            stage for stage in self.render_stage_sources() if stage != "critic"
        ]
        return non_critic_sources[-1] if non_critic_sources else None

    def to_metadata(self, exp_mode: str) -> dict[str, object]:
        return {
            "exp_mode": exp_mode,
            "stages": list(self.stages),
            "render_stage_sources": list(self.render_stage_sources()),
            "base_render_source": self.base_render_source(),
            "eval_image_source": self.eval_image_source,
            "critic_source": self.critic_source,
            "disable_eval": self.disable_eval,
        }


PIPELINE_SPECS: dict[str, PipelineSpec] = {
    "vanilla": PipelineSpec(
        stages=("vanilla",),
        eval_image_source="vanilla",
    ),
    "dev_planner": PipelineSpec(
        stages=("retriever", "planner", "visualizer"),
        eval_image_source="planner",
    ),
    "dev_planner_stylist": PipelineSpec(
        stages=("retriever", "planner", "stylist", "visualizer"),
        eval_image_source="stylist",
    ),
    "dev_planner_critic": PipelineSpec(
        stages=("retriever", "planner", "visualizer", "critic"),
        critic_source="planner",
    ),
    "demo_planner_critic": PipelineSpec(
        stages=("retriever", "planner", "visualizer", "critic"),
        critic_source="planner",
        disable_eval=True,
    ),
    "dev_full": PipelineSpec(
        stages=("retriever", "planner", "stylist", "visualizer", "critic"),
        critic_source="stylist",
    ),
    "demo_full": PipelineSpec(
        stages=("retriever", "planner", "stylist", "visualizer", "critic"),
        critic_source="stylist",
        disable_eval=True,
    ),
    "dev_polish": PipelineSpec(
        stages=("polish",),
        eval_image_source="polish",
    ),
    "dev_retriever": PipelineSpec(
        stages=("retriever",),
        disable_eval=True,
    ),
}


def get_pipeline_spec(exp_mode: str) -> PipelineSpec:
    try:
        return PIPELINE_SPECS[exp_mode]
    except KeyError as exc:
        raise ValueError(f"Unknown experiment name: {exp_mode}") from exc


def get_supported_exp_modes() -> tuple[str, ...]:
    return tuple(PIPELINE_SPECS.keys())


def get_pipeline_metadata(exp_mode: str) -> dict[str, object]:
    return get_pipeline_spec(exp_mode).to_metadata(exp_mode)
