"""Typed Studio workflow metadata and explicit runtime options."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from paperbanana.connections.models import ConnectionRole
from paperbanana.core.types import DiagramType


@dataclass(frozen=True)
class StudioWorkflowSpec:
    """One production page and the backend capabilities it may consume."""

    key: str
    label_key: str
    group_key: str
    required_roles: tuple[ConnectionRole, ...] = ()
    dynamic_roles: bool = False
    uses_image_size: bool = False


@dataclass(frozen=True)
class StudioRunOptions:
    """Explicit non-task parameters used to construct one Settings object."""

    output_dir: str
    config_path: str | None = None
    vlm_profile_id: str | None = None
    image_profile_id: str | None = None
    output_format: str = "png"
    output_resolution: str = "2k"
    refinement_iterations: int = 3
    auto_refine: bool = False
    max_iterations: int = 30
    optimize_inputs: bool = False
    save_prompts: bool = True
    seed: int | None = None


WORKFLOW_SPECS = (
    StudioWorkflowSpec(
        "diagram",
        "tab.diagram",
        "nav.generate",
        (ConnectionRole.VLM, ConnectionRole.IMAGE),
        uses_image_size=True,
    ),
    StudioWorkflowSpec("plot", "tab.plot", "nav.generate", (ConnectionRole.VLM,)),
    StudioWorkflowSpec("continue", "tab.continue", "nav.improve", dynamic_roles=True),
    StudioWorkflowSpec("evaluate", "tab.evaluate", "nav.improve", (ConnectionRole.VLM,)),
    StudioWorkflowSpec(
        "orchestrate",
        "tab.orchestrate",
        "nav.automation",
        (ConnectionRole.VLM, ConnectionRole.IMAGE),
    ),
    StudioWorkflowSpec("batch", "tab.batch", "nav.automation", dynamic_roles=True),
    StudioWorkflowSpec(
        "sweep",
        "tab.sweep",
        "nav.automation",
        (ConnectionRole.VLM, ConnectionRole.IMAGE),
    ),
    StudioWorkflowSpec("composite", "tab.composite", "nav.tools"),
    StudioWorkflowSpec("runs", "tab.runs", "nav.tools"),
    StudioWorkflowSpec("settings", "settings.title", "nav.system"),
)
WORKFLOW_BY_KEY = {spec.key: spec for spec in WORKFLOW_SPECS}


def roles_for_diagram_type(diagram_type: str | DiagramType) -> tuple[ConnectionRole, ...]:
    """Return the exact model roles used by a diagram type."""
    normalized = DiagramType(diagram_type)
    if normalized == DiagramType.STATISTICAL_PLOT:
        return (ConnectionRole.VLM,)
    return (ConnectionRole.VLM, ConnectionRole.IMAGE)


def roles_for_batch_type(batch_type: str) -> tuple[ConnectionRole, ...]:
    """Return model roles for the selected batch workflow."""
    return roles_for_diagram_type(batch_type)


def roles_for_saved_run(output_dir: str, run_id: str) -> tuple[ConnectionRole, ...]:
    """Read the persisted run type before resolving connections for continuation."""
    run_input = Path(output_dir).expanduser() / run_id / "run_input.json"
    if not run_input.is_file():
        raise FileNotFoundError(f"run_input.json not found for run: {run_id}")
    try:
        payload = json.loads(run_input.read_text(encoding="utf-8"))
        return roles_for_diagram_type(payload["diagram_type"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid diagram_type in {run_input}") from exc
