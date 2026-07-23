"""Async pipeline runners with progress text for the Studio UI."""

from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Optional

from paperbanana.connections.manager import ConnectionManager
from paperbanana.connections.models import ConnectionRole
from paperbanana.connections.resolver import load_runtime_settings
from paperbanana.core.config import Settings
from paperbanana.core.logging import configure_logging
from paperbanana.core.pipeline import PaperBananaPipeline
from paperbanana.core.plot_data import load_statistical_plot_payload
from paperbanana.core.resume import load_resume_state
from paperbanana.core.source_loader import load_methodology_source
from paperbanana.core.sweep import (
    build_sweep_variants,
    parse_csv_bools,
    parse_csv_ints,
    parse_csv_values,
    quality_proxy_score,
    rank_sweep_results,
    summarize_sweep,
)
from paperbanana.core.types import (
    ASPECT_RATIO_VALUES,
    DiagramType,
    GenerationInput,
    PipelineProgressEvent,
    PipelineProgressStage,
)
from paperbanana.core.utils import ensure_dir, find_prompt_dir, generate_run_id, save_json
from paperbanana.evaluation.judge import VLMJudge
from paperbanana.i18n import get_translator, localize_error
from paperbanana.providers.registry import ProviderRegistry

ASPECT_RATIO_CHOICES = [
    "default",
    *ASPECT_RATIO_VALUES,
]
REFERENCE_CATEGORY_CHOICES = [
    "",
    "agent_reasoning",
    "generative_learning",
    "healthcare_medical",
    "multimodal_fusion",
    "nlp_language",
    "optimization_theory",
    "robotics_control",
    "science_applications",
    "systems_networking",
    "vision_perception",
]


def read_text_file(path: str | None, max_chars: int = 500_000) -> str:
    """Read UTF-8 text from a path; empty string if missing."""
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[truncated]"
    return text


def merge_context(text: str, file_path: str | None) -> str:
    """Prefer uploaded file content when present; otherwise use text box."""
    from_file = read_text_file(file_path)
    if from_file.strip():
        return from_file
    return (text or "").strip()


def build_settings(
    *,
    config_path: Optional[str],
    output_dir: str,
    vlm_provider: str,
    vlm_model: str,
    image_provider: str,
    image_model: str,
    output_format: str,
    refinement_iterations: int,
    auto_refine: bool,
    max_iterations: int,
    optimize_inputs: bool,
    save_prompts: bool,
    output_resolution: str = "2k",
    seed: Optional[int] = None,
    reference_category: Optional[list[str]] = None,
    connection_manager: ConnectionManager | None = None,
    vlm_profile_id: str | None = None,
    image_profile_id: str | None = None,
    legacy_connections: bool = False,
    required_roles: tuple[ConnectionRole, ...] = (
        ConnectionRole.VLM,
        ConnectionRole.IMAGE,
    ),
) -> Settings:
    """Build pipeline settings and resolve exactly one connection source."""
    overrides: dict[str, Any] = {
        "output_dir": output_dir,
        "output_resolution": output_resolution,
        "output_format": output_format.lower(),
        "refinement_iterations": int(refinement_iterations),
        "auto_refine": bool(auto_refine),
        "max_iterations": int(max_iterations),
        "optimize_inputs": bool(optimize_inputs),
        "save_prompts": bool(save_prompts),
    }
    if seed is not None and str(seed).strip() != "":
        try:
            overrides["seed"] = int(seed)
        except ValueError:
            pass
    if reference_category:
        overrides["reference_category"] = reference_category
    if not legacy_connections and ConnectionRole.IMAGE not in required_roles:
        overrides["image_provider"] = "none"
    if legacy_connections:
        base_defaults = Settings()
        overrides.update(
            {
                "vlm_provider": vlm_provider.strip() or "gemini",
                "vlm_model": vlm_model.strip() or base_defaults.vlm_model,
                "image_provider": image_provider.strip() or "google_imagen",
                "image_model": image_model.strip() or base_defaults.image_model,
            }
        )

    normalized_config = (str(config_path).strip() if config_path else "") or None
    return load_runtime_settings(
        config_path=normalized_config,
        overrides=overrides,
        manager=connection_manager,
        vlm_profile_id=vlm_profile_id,
        image_profile_id=image_profile_id,
        legacy=legacy_connections,
        required_roles=required_roles,
    )


class ProgressLog:
    """Collect human-readable lines from ``PipelineProgressEvent`` callbacks."""

    def __init__(self, locale: str = "en") -> None:
        self.lines: list[str] = []
        self.t = get_translator(locale)

    def append(self, line: str) -> None:
        self.lines.append(line)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def handler(self) -> Callable[[PipelineProgressEvent], None]:
        def _on(event: PipelineProgressEvent) -> None:
            self._dispatch(event)

        return _on

    def _dispatch(self, event: PipelineProgressEvent) -> None:
        st = event.stage
        sec = f" ({event.seconds:.1f}s)" if event.seconds is not None else ""
        if st == PipelineProgressStage.OPTIMIZER_START:
            self.append(self.t("progress.optimizer_start"))
        elif st == PipelineProgressStage.OPTIMIZER_END:
            self.append(self.t("progress.optimizer_end", seconds=sec))
        elif st == PipelineProgressStage.RETRIEVER_START:
            self.append(self.t("progress.retriever_start"))
        elif st == PipelineProgressStage.RETRIEVER_END:
            n = (event.extra or {}).get("examples_count", "?")
            self.append(self.t("progress.retriever_end", count=n, seconds=sec))
        elif st == PipelineProgressStage.PLANNER_START:
            self.append(self.t("progress.planner_start"))
        elif st == PipelineProgressStage.PLANNER_END:
            ratio = (event.extra or {}).get("recommended_ratio")
            extra = self.t("progress.ratio", ratio=ratio) if ratio else ""
            self.append(self.t("progress.planner_end", seconds=sec, ratio=extra))
        elif st == PipelineProgressStage.STYLIST_START:
            self.append(self.t("progress.stylist_start"))
        elif st == PipelineProgressStage.STYLIST_END:
            self.append(self.t("progress.stylist_end", seconds=sec))
        elif st == PipelineProgressStage.STRUCTURER_START:
            self.append(self.t("progress.structurer_start"))
        elif st == PipelineProgressStage.STRUCTURER_END:
            ex = event.extra or {}
            if ex.get("error"):
                self.append(self.t("progress.structurer_failed", seconds=sec))
            else:
                self.append(self.t("progress.structurer_end", seconds=sec))
        elif st == PipelineProgressStage.VISUALIZER_START:
            it = event.iteration or "?"
            tot = (event.extra or {}).get("total_iterations")
            tot_s = f"/{tot}" if tot else ""
            self.append(self.t("progress.visualizer_start", iteration=it, total=tot_s))
        elif st == PipelineProgressStage.VISUALIZER_END:
            self.append(self.t("progress.visualizer_end", seconds=sec))
        elif st == PipelineProgressStage.CRITIC_START:
            self.append(self.t("progress.critic_start"))
        elif st == PipelineProgressStage.CRITIC_END:
            ex = event.extra or {}
            if ex.get("needs_revision"):
                self.append(self.t("progress.critic_revision", seconds=sec))
                for s in (ex.get("critic_suggestions") or [])[:5]:
                    self.append(f"  • {s}")
            else:
                self.append(self.t("progress.critic_satisfied", seconds=sec))


def _aspect_ratio_value(label: str) -> Optional[str]:
    if not label or label == "default":
        return None
    return label


def _actual_image_size(path: str) -> str | None:
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
        return f"{width}x{height} px"
    except (OSError, ValueError):
        return None


def run_methodology(
    settings: Settings,
    source_context: str,
    caption: str,
    aspect_ratio_label: str,
    reference_ids: Optional[str] = None,
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, Optional[str], list[tuple[str, str]], str]:
    """Run methodology diagram generation. Returns (log, final_path, gallery, error)."""
    configure_logging(verbose=verbose_logging)
    log = ProgressLog(locale)
    log.append(log.t("run.methodology_start"))
    err = ""
    try:
        ref_id_list = None
        if reference_ids:
            ref_id_list = [rid.strip() for rid in reference_ids.split(",") if rid.strip()]
        gen_in = GenerationInput(
            source_context=source_context,
            communicative_intent=caption.strip(),
            diagram_type=DiagramType.METHODOLOGY,
            aspect_ratio=_aspect_ratio_value(aspect_ratio_label),
            reference_ids=ref_id_list,
        )

        async def _go():
            pipeline = PaperBananaPipeline(settings=settings)
            return await pipeline.generate(gen_in, progress_callback=log.handler())

        result = asyncio.run(_go())
        log.append("")
        log.append(log.t("run.complete", run_id=result.metadata.get("run_id", "?")))
        log.append(log.t("run.final_image", path=result.image_path))
        actual_size = _actual_image_size(result.image_path)
        if actual_size:
            log.append(log.t("run.actual_size", size=actual_size))
        gallery: list[tuple[str, str]] = []
        for rec in result.iterations:
            p = Path(rec.image_path)
            if p.is_file():
                gallery.append((str(p), f"iter {rec.iteration}"))
        final = result.image_path
        fp = final if Path(final).is_file() else None
        return log.text, fp, gallery, ""
    except Exception as e:
        err = localize_error(e, log.t)
        log.append("")
        log.append(log.t("run.failed"))
        log.append(err)
        return log.text, None, [], err


def run_plot(
    settings: Settings,
    data_path: str,
    intent: str,
    aspect_ratio_label: str,
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, Optional[str], list[tuple[str, str]], str]:
    """Run statistical plot pipeline from CSV or JSON path."""
    configure_logging(verbose=verbose_logging)
    log = ProgressLog(locale)
    log.append(log.t("run.plot_start"))
    path = Path(data_path)
    if not path.is_file():
        msg = f"Data file not found: {data_path}"
        log.append(msg)
        return log.text, None, [], msg

    try:
        source_context, raw_data = load_statistical_plot_payload(path)

        gen_in = GenerationInput(
            source_context=source_context,
            communicative_intent=intent.strip(),
            diagram_type=DiagramType.STATISTICAL_PLOT,
            raw_data={"data": raw_data},
            aspect_ratio=_aspect_ratio_value(aspect_ratio_label),
        )

        async def _go():
            pipeline = PaperBananaPipeline(settings=settings)
            return await pipeline.generate(gen_in, progress_callback=log.handler())

        result = asyncio.run(_go())
        log.append("")
        log.append(log.t("run.complete", run_id=result.metadata.get("run_id", "?")))
        actual_size = _actual_image_size(result.image_path)
        if actual_size:
            log.append(log.t("run.actual_size", size=actual_size))
        gallery: list[tuple[str, str]] = []
        for rec in result.iterations:
            p = Path(rec.image_path)
            if p.is_file():
                gallery.append((str(p), f"iter {rec.iteration}"))
        fp = result.image_path if Path(result.image_path).is_file() else None
        return log.text, fp, gallery, ""
    except Exception as e:
        err = localize_error(e, log.t)
        log.append("")
        log.append(log.t("run.failed"))
        log.append(err)
        return log.text, None, [], err


def run_evaluate(
    settings: Settings,
    generated_path: str,
    reference_path: str,
    source_context: str,
    caption: str,
    evaluation_task: DiagramType = DiagramType.METHODOLOGY,
    plot_data_path: str = "",
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, str]:
    """VLM judge comparative evaluation. Returns (log, formatted results)."""
    configure_logging(verbose=verbose_logging)
    t = get_translator(locale)
    task_key = (
        "choice.statistical_plot"
        if evaluation_task == DiagramType.STATISTICAL_PLOT
        else "choice.methodology"
    )
    task_label = t(task_key)
    lines: list[str] = [t("evaluate.start", task=task_label)]
    gp = Path(generated_path)
    rp = Path(reference_path)
    if not gp.is_file():
        msg = t("evaluate.generated_missing", path=generated_path)
        lines.append(msg)
        return "\n".join(lines), msg
    if not rp.is_file():
        msg = t("evaluate.reference_missing", path=reference_path)
        lines.append(msg)
        return "\n".join(lines), msg
    effective_context = source_context
    if evaluation_task == DiagramType.STATISTICAL_PLOT:
        plot_path = Path(plot_data_path)
        if not plot_path.is_file():
            msg = t("evaluate.plot_data_missing", path=plot_data_path)
            lines.append(msg)
            return "\n".join(lines), msg
        try:
            effective_context, _ = load_statistical_plot_payload(plot_path)
        except ValueError as e:
            msg = t("evaluate.plot_data_invalid", error=e)
            lines.append(msg)
            return "\n".join(lines), msg

    if not effective_context.strip():
        msg = t("error.context_empty")
        lines.append(msg)
        return "\n".join(lines), msg

    try:
        vlm = ProviderRegistry.create_vlm(settings)
        judge = VLMJudge(vlm, prompt_dir=find_prompt_dir())

        async def _go():
            return await judge.evaluate(
                image_path=str(gp),
                source_context=effective_context,
                caption=caption.strip(),
                reference_path=str(rp),
                task=evaluation_task,
            )

        scores = asyncio.run(_go())
        lines.append(t("common.done"))
        dims = ["faithfulness", "conciseness", "readability", "aesthetics"]
        out_parts = [f"## {t('evaluate.results')} ({task_label})\n"]
        for dim in dims:
            r = getattr(scores, dim)
            out_parts.append(
                f"**{t(f'evaluate.dimension.{dim}')}** - "
                f"{r.winner} ({t('evaluate.score', score=r.score)})\n"
            )
            if r.reasoning:
                out_parts.append(f"{r.reasoning}\n\n")
        out_parts.append(
            f"### {t('evaluate.overall')}\n**{scores.overall_winner}** - "
            f"{t('evaluate.score', score=scores.overall_score)}\n"
        )
        return "\n".join(lines), "".join(out_parts)
    except Exception as e:
        err = localize_error(e, t)
        lines.append(t("run.failed"))
        lines.append(err)
        return "\n".join(lines), err


def run_continue(
    settings: Settings,
    output_dir: str,
    run_id: str,
    user_feedback: str,
    additional_iterations: Optional[int],
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, Optional[str], list[tuple[str, str]], str]:
    """Continue an existing run directory."""
    configure_logging(verbose=verbose_logging)
    log = ProgressLog(locale)
    log.append(log.t("continue.start", run_id=run_id))
    try:
        state = load_resume_state(output_dir, run_id.strip())
    except (FileNotFoundError, ValueError) as e:
        msg = localize_error(e, log.t)
        log.append(msg)
        return log.text, None, [], msg

    try:
        extra_it = None
        if additional_iterations and additional_iterations > 0:
            extra_it = additional_iterations

        async def _go():
            pipeline = PaperBananaPipeline(settings=settings)
            return await pipeline.continue_run(
                resume_state=state,
                additional_iterations=extra_it,
                user_feedback=user_feedback.strip() or None,
                progress_callback=log.handler(),
            )

        result = asyncio.run(_go())
        log.append("")
        log.append(log.t("continue.complete", path=result.image_path))
        gallery: list[tuple[str, str]] = []
        for rec in result.iterations:
            p = Path(rec.image_path)
            if p.is_file():
                gallery.append((str(p), f"iter {rec.iteration}"))
        fp = result.image_path if Path(result.image_path).is_file() else None
        return log.text, fp, gallery, ""
    except Exception as e:
        err = localize_error(e, log.t)
        log.append("")
        log.append(log.t("run.failed"))
        log.append(err)
        return log.text, None, [], err


def _localize_workflow_message(t: Callable[..., str], message: str) -> str:
    """Translate the finite progress vocabulary emitted by the shared batch runner."""
    patterns = (
        (r"Nothing to run; report at (.+)", "batch.nothing", ("path",)),
        (r"Item (\d+)/(\d+) (.+): input missing", "batch.input_missing", ("index", "total", "id")),
        (r"Item (\d+)/(\d+) (.+): data missing", "batch.data_missing", ("index", "total", "id")),
        (r"Item (\d+)/(\d+) (.+): ok -> (.+)", "batch.item_ok", ("index", "total", "id", "path")),
        (
            r"Item (.+): retry (\d+)/(\d+) after (.+)",
            "batch.item_retry",
            ("id", "attempt", "total", "error"),
        ),
        (
            r"Item (\d+)/(\d+) (.+): failed - (.+)",
            "batch.item_failed",
            ("index", "total", "id", "error"),
        ),
        (r"Composite: (.+)", "batch.composite", ("path",)),
        (
            r"\[green\](\d+)/(\d+) (.+): ok -> (.+)\[/green\]",
            "batch.item_ok",
            ("index", "total", "id", "path"),
        ),
        (
            r"\[yellow\](.+): retry (\d+)/(\d+) after (.+)\[/yellow\]",
            "batch.item_retry",
            ("id", "attempt", "total", "error"),
        ),
        (
            r"\[red\](\d+)/(\d+) (.+): failed - (.+)\[/red\]",
            "batch.item_failed",
            ("index", "total", "id", "error"),
        ),
    )
    for pattern, key, fields in patterns:
        match = re.fullmatch(pattern, message)
        if match:
            return t(key, **dict(zip(fields, match.groups())))
    return message


def run_batch(
    settings: Settings,
    manifest_path: str,
    *,
    resume_batch: Optional[str] = None,
    retry_failed: bool = False,
    max_retries: int = 0,
    concurrency: int = 1,
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, str]:
    """Run batch manifest; returns (log, batch_dir path or error note)."""
    from paperbanana.core.workflow_runner import run_methodology_batch

    configure_logging(verbose=verbose_logging)
    t = get_translator(locale)
    lines: list[str] = [t("batch.start_methodology")]
    try:
        result = run_methodology_batch(
            manifest_path=Path(manifest_path),
            output_dir=Path(settings.output_dir),
            runtime_settings=settings,
            format=str(settings.output_format),
            resume_batch=resume_batch,
            retry_failed=retry_failed,
            max_retries=max(0, max_retries),
            concurrency=max(1, concurrency),
            progress_callback=lambda message: lines.append(_localize_workflow_message(t, message)),
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        message = t("batch.failed", error=exc)
        lines.append(message)
        return "\n".join(lines), message
    lines.append(
        t(
            "batch.summary",
            succeeded=result["succeeded"],
            failed=result["failed"],
            skipped=result["skipped"],
        )
    )
    lines.append(t("batch.report", path=result["batch_report_path"]))
    return "\n".join(lines), str(result["batch_dir"])


def run_plot_batch(
    settings: Settings,
    manifest_path: str,
    default_aspect_ratio_label: str = "default",
    *,
    resume_batch: Optional[str] = None,
    retry_failed: bool = False,
    max_retries: int = 0,
    concurrency: int = 1,
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, str]:
    """Run plot batch manifest; returns (log, batch_dir path or error note)."""
    from paperbanana.core.workflow_runner import run_plot_batch as run_shared_plot_batch

    configure_logging(verbose=verbose_logging)
    t = get_translator(locale)
    lines: list[str] = [t("batch.start_plot")]
    try:
        result = run_shared_plot_batch(
            manifest_path=Path(manifest_path),
            output_dir=Path(settings.output_dir),
            runtime_settings=settings,
            format=str(settings.output_format),
            aspect_ratio=_aspect_ratio_value(default_aspect_ratio_label),
            resume_batch=resume_batch,
            retry_failed=retry_failed,
            max_retries=max(0, max_retries),
            concurrency=max(1, concurrency),
            progress_callback=lambda message: lines.append(_localize_workflow_message(t, message)),
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        message = t("batch.failed", error=exc)
        lines.append(message)
        return "\n".join(lines), message
    lines.append(
        t(
            "batch.summary",
            succeeded=result["succeeded"],
            failed=result["failed"],
            skipped=result["skipped"],
        )
    )
    lines.append(t("batch.report", path=result["batch_report_path"]))
    return "\n".join(lines), str(result["batch_dir"])


def _preview_json_file(path: Path, *, max_chars: int = 10_000) -> str:
    """Load JSON (or raw text) from disk for Studio previews."""
    if not path.is_file():
        return ""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except (OSError, json.JSONDecodeError):
        text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n… [truncated]"
    return text


def run_orchestration(
    settings: Settings,
    paper_file_path: str | None,
    resume_orchestrate: str | None,
    data_dir: str | None,
    max_method_figures: int,
    max_plot_figures: int,
    pdf_pages: str | None,
    dry_run: bool,
    venue: str,
    retry_failed: bool,
    max_retries: int,
    concurrency: int,
    config_path: str | None,
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, str, str, str]:
    """Run figure-package orchestration (CLI parity).

    Returns (log, orch_dir, plan_preview, package_preview).
    """
    from paperbanana.core.workflow_runner import run_orchestration_package

    configure_logging(verbose=verbose_logging)
    t = get_translator(locale)
    lines: list[str] = [t("orchestration.start"), ""]

    def emit(msg: str) -> None:
        lines.append(_localize_workflow_message(t, msg))

    resume = (resume_orchestrate or "").strip() or None
    paper_upload = (paper_file_path or "").strip() or None
    if paper_upload and not Path(paper_upload).is_file():
        paper_upload = None

    if resume and paper_upload:
        msg = t("orchestration.resume_conflict")
        lines.append(msg)
        return "\n".join(lines), "", "", ""

    if not resume and (not paper_upload or not Path(paper_upload).is_file()):
        msg = t("orchestration.paper_required")
        lines.append(msg)
        return "\n".join(lines), "", "", ""

    if not resume:
        paper_arg: str | None = paper_upload
    else:
        paper_arg = None

    data_arg = (data_dir or "").strip() or None
    pages_arg = (pdf_pages or "").strip() or None
    if resume:
        data_arg = None
        pages_arg = None

    cfg = (config_path or "").strip() or None
    # Venue names (built-in and user packs) are validated downstream by
    # run_orchestration_package; unknown names raise listing available venues.
    venue_s = (venue or "neurips").strip().lower()

    max_m = max(1, int(max_method_figures or 1))
    max_p = max(0, int(max_plot_figures or 0))
    mret = max(0, int(max_retries or 0))
    conc = max(1, int(concurrency or 1))

    out_root = Path((settings.output_dir or "outputs").strip() or "outputs")

    out_fmt = str(settings.output_format)
    if out_fmt not in ("png", "jpeg", "webp"):
        lines.append(t("orchestration.format_fallback", format=out_fmt))
        lines.append("")
        out_fmt = "png"

    try:
        result = run_orchestration_package(
            paper=paper_arg,
            resume_orchestrate=resume,
            output_dir=out_root,
            data_dir=data_arg,
            max_method_figures=max_m,
            max_plot_figures=max_p,
            pdf_pages=pages_arg,
            dry_run=bool(dry_run),
            config=cfg,
            vlm_provider=None,
            vlm_model=None,
            image_provider=None,
            image_model=None,
            runtime_settings=settings,
            iterations=settings.refinement_iterations,
            auto=settings.auto_refine,
            max_iterations=settings.max_iterations,
            optimize=settings.optimize_inputs,
            format=out_fmt,
            save_prompts=settings.save_prompts,
            venue=venue_s,
            retry_failed=bool(retry_failed),
            max_retries=mret,
            concurrency=conc,
            progress_callback=emit,
            after_plan_callback=None,
        )
    except (FileNotFoundError, ValueError, ImportError, RuntimeError) as e:
        lines.append(t("orchestration.failed", error=localize_error(e, t)))
        return "\n".join(lines), "", "", ""
    except Exception as e:
        lines.append(t("orchestration.failed", error=localize_error(e, t)))
        return "\n".join(lines), "", "", ""

    orch_dir = str(result.get("orchestrate_dir") or "")
    plan_path = Path(str(result.get("orchestration_plan_path") or ""))

    lines.append("")
    if result.get("dry_run"):
        lines.append(t("orchestration.dry_complete"))
        plan_preview = _preview_json_file(plan_path)
        pkg_preview = t("orchestration.dry_package")
        return "\n".join(lines), orch_dir, plan_preview, pkg_preview

    gen_n = result.get("generated_count", 0)
    fail_n = result.get("failed_count", 0)
    ok = result.get("strict_success")
    lines.append(t("orchestration.summary", generated=gen_n, failed=fail_n, success=ok))
    if result.get("figure_package_path"):
        lines.append(t("orchestration.package", path=result["figure_package_path"]))
    if result.get("figures_tex_path"):
        lines.append(t("orchestration.latex", path=result["figures_tex_path"]))
    if result.get("captions_md_path"):
        lines.append(t("orchestration.captions", path=result["captions_md_path"]))

    plan_preview = _preview_json_file(plan_path)
    pkg_path = Path(str(result.get("figure_package_path") or ""))
    pkg_preview = _preview_json_file(pkg_path) if pkg_path.is_file() else ""
    if not pkg_preview and result.get("figure_package_path"):
        pkg_preview = t("orchestration.package_unreadable", path=pkg_path)

    return "\n".join(lines), orch_dir, plan_preview, pkg_preview


def run_sweep(
    settings: Settings,
    *,
    input_path: str,
    caption: str,
    pdf_pages: Optional[str] = None,
    vlm_providers: str = "",
    vlm_models: str = "",
    image_providers: str = "",
    image_models: str = "",
    iterations: str = "",
    optimize_modes: str = "",
    auto_modes: str = "",
    max_variants: Optional[int] = None,
    dry_run: bool = False,
    verbose_logging: bool = False,
    locale: str = "en",
) -> tuple[str, str, str]:
    """Run sweep using core sweep utilities. Returns (log, sweep_dir, report_path)."""
    configure_logging(verbose=verbose_logging)
    t = get_translator(locale)
    lines: list[str] = [t("sweep.start")]
    input_file = Path(input_path)
    if not input_file.is_file():
        msg = t("sweep.input_missing", path=input_path)
        lines.append(msg)
        return "\n".join(lines), "", ""
    if not caption.strip():
        msg = t("error.caption_required")
        lines.append(msg)
        return "\n".join(lines), "", ""
    if max_variants is not None and max_variants < 1:
        msg = t("sweep.max_variants_invalid")
        lines.append(msg)
        return "\n".join(lines), "", ""

    connection_axes = any(
        parse_csv_values(value)
        for value in (vlm_providers, vlm_models, image_providers, image_models)
    )
    if connection_axes and settings.connection_source != "legacy":
        msg = t("sweep.profile_axes_forbidden")
        lines.append(msg)
        return "\n".join(lines), "", ""

    try:
        variants = build_sweep_variants(
            vlm_providers=parse_csv_values(vlm_providers) or [settings.vlm_provider],
            vlm_models=parse_csv_values(vlm_models) or [settings.effective_vlm_model],
            image_providers=parse_csv_values(image_providers) or [settings.image_provider],
            image_models=parse_csv_values(image_models) or [settings.effective_image_model],
            refinement_iterations=parse_csv_ints(iterations, field_name="iterations"),
            optimize_inputs=parse_csv_bools(optimize_modes, field_name="optimize_modes"),
            auto_refine=parse_csv_bools(auto_modes, field_name="auto_modes"),
            max_variants=max_variants,
        )
    except ValueError as e:
        lines.append(localize_error(e, t))
        return "\n".join(lines), "", ""
    if not variants:
        lines.append(t("sweep.empty"))
        return "\n".join(lines), "", ""

    try:
        source_context = load_methodology_source(input_file, pdf_pages=pdf_pages)
    except Exception as e:
        lines.append(localize_error(e, t))
        return "\n".join(lines), "", ""

    sweep_id = f"sweep_{generate_run_id()}"
    sweep_dir = ensure_dir(Path(settings.output_dir) / sweep_id)
    report_path = sweep_dir / "sweep_report.json"
    lines.append(t("sweep.id", sweep_id=sweep_id))
    lines.append(t("sweep.variants", count=len(variants)))
    lines.append(t("sweep.output", path=sweep_dir))

    if dry_run:
        preview = [variant.as_dict() for variant in variants[: min(10, len(variants))]]
        report = {
            "sweep_id": sweep_id,
            "status": "dry_run",
            "input": str(input_file.resolve()),
            "caption": caption,
            "total_variants": len(variants),
            "preview": preview,
        }
        save_json(report, report_path)
        lines.append(t("sweep.dry_complete"))
        lines.append(t("batch.report", path=report_path))
        return "\n".join(lines), str(sweep_dir), str(report_path)

    all_results: list[dict[str, Any]] = []
    total_start = time.perf_counter()
    gen_input = GenerationInput(
        source_context=source_context,
        communicative_intent=caption.strip(),
        diagram_type=DiagramType.METHODOLOGY,
    )

    for idx, variant in enumerate(variants, start=1):
        lines.append(t("sweep.variant", index=idx, total=len(variants), id=variant.variant_id))
        variant_dir = ensure_dir(sweep_dir / variant.variant_id)
        overrides: dict[str, Any] = {
            "output_dir": str(variant_dir),
            "output_format": settings.output_format,
            "vlm_provider": variant.vlm_provider,
            "image_provider": variant.image_provider,
            "refinement_iterations": variant.refinement_iterations,
            "optimize_inputs": variant.optimize_inputs,
            "auto_refine": variant.auto_refine,
        }
        if variant.vlm_model:
            overrides["vlm_model"] = variant.vlm_model
        if variant.image_model:
            overrides["image_model"] = variant.image_model
        variant_settings = settings.model_copy(update=overrides)
        try:
            variant_start = time.perf_counter()
            result = asyncio.run(PaperBananaPipeline(settings=variant_settings).generate(gen_input))
            variant_seconds = time.perf_counter() - variant_start
            final_critique = result.iterations[-1].critique if result.iterations else None
            suggestion_count = len(final_critique.critic_suggestions) if final_critique else 0
            score = quality_proxy_score(suggestion_count)
            all_results.append(
                {
                    "status": "success",
                    **variant.as_dict(),
                    "run_id": result.metadata.get("run_id"),
                    "output_path": result.image_path,
                    "iterations_used": len(result.iterations),
                    "critic_suggestions": suggestion_count,
                    "quality_proxy_score": round(score, 2),
                    "total_seconds": round(variant_seconds, 2),
                }
            )
            lines.append(t("sweep.variant_ok", score=score, seconds=variant_seconds))
        except Exception as e:
            safe_error = localize_error(e, t)
            all_results.append(
                {
                    "status": "failed",
                    **variant.as_dict(),
                    "error": safe_error,
                }
            )
            lines.append(t("sweep.variant_failed", error=safe_error))

    successful_results = [item for item in all_results if item["status"] == "success"]
    ranked_results = rank_sweep_results(successful_results)
    summary = summarize_sweep(all_results)
    report = {
        "sweep_id": sweep_id,
        "status": "completed",
        "input": str(input_file.resolve()),
        "caption": caption,
        "total_seconds": round(time.perf_counter() - total_start, 2),
        "summary": summary,
        "results": all_results,
        "ranked_results": ranked_results,
        "quality_proxy_note": (
            "quality_proxy_score = max(0, 100 - 12.5 * N) where N is critic suggestion "
            "count on the final iteration"
        ),
    }
    save_json(report, report_path)
    lines.append("")
    lines.append(t("sweep.completed", count=summary.get("completed", 0)))
    lines.append(t("sweep.failed", count=summary.get("failed", 0)))
    lines.append(t("sweep.best", variant=summary.get("best_variant")))
    lines.append(t("batch.report", path=report_path))
    return "\n".join(lines), str(sweep_dir), str(report_path)


def _sanitize_output_filename(name: str) -> str:
    """Strip directory components and reject traversal attempts."""
    cleaned = (name or "").strip() or "composite.png"
    base = Path(cleaned).name
    if not base or base in (".", ".."):
        return "composite.png"
    return base


def run_composite(
    image_paths: list[str],
    *,
    output_dir: str,
    layout: str = "auto",
    labels: str = "",
    spacing: int = 20,
    label_position: str = "bottom",
    label_font_size: int = 32,
    output_filename: str = "composite.png",
    locale: str = "en",
) -> tuple[str, Optional[str]]:
    """Compose multiple uploaded images into a single labeled multi-panel figure.

    Returns (log, output_path). output_path is None on failure.
    """
    from typing import Literal, cast

    from paperbanana.core.composite import compose_images

    t = get_translator(locale)
    lines: list[str] = [t("composite.start")]

    valid_paths = [p for p in image_paths if p and Path(p).is_file()]
    if not valid_paths:
        msg = t("composite.images_required")
        lines.append(msg)
        return "\n".join(lines), None

    if label_position not in ("top", "bottom"):
        msg = t("composite.position_invalid", value=label_position)
        lines.append(msg)
        return "\n".join(lines), None

    if spacing < 0:
        msg = t("composite.spacing_invalid", value=spacing)
        lines.append(msg)
        return "\n".join(lines), None

    if label_font_size <= 0:
        msg = t("composite.font_invalid", value=label_font_size)
        lines.append(msg)
        return "\n".join(lines), None

    label_list: Optional[list[str]] = None
    auto_label = True
    stripped_labels = labels.strip()
    if stripped_labels:
        if stripped_labels.lower() == "none":
            auto_label = False
        else:
            label_list = [item.strip() for item in labels.split(",") if item.strip()]
            auto_label = False

    out_dir_str = (output_dir or "").strip() or "outputs"
    out_dir = Path(out_dir_str).resolve()
    ensure_dir(out_dir)
    safe_name = _sanitize_output_filename(output_filename)
    output_path = out_dir / safe_name

    lines.append(t("composite.panels", count=len(valid_paths)))
    lines.append(t("composite.layout", layout=layout))
    lines.append(t("composite.output", path=output_path))

    try:
        compose_images(
            image_paths=valid_paths,
            layout=layout,
            labels=label_list,
            auto_label=auto_label,
            spacing=spacing,
            label_position=cast(Literal["top", "bottom"], label_position),
            label_font_size=label_font_size,
            output_path=output_path,
        )
    except (ValueError, OSError) as e:
        lines.append(t("run.failed"))
        lines.append(localize_error(e, t))
        return "\n".join(lines), None
    except Exception as e:
        lines.append(t("run.failed"))
        lines.append(localize_error(e, t))
        return "\n".join(lines), None

    lines.append(t("common.done"))
    return "\n".join(lines), str(output_path)
