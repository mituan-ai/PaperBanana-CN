"""Corpus-grounded style-guide synthesis via VLM map-reduce.

Ports the upstream ``generate_category_style_guide`` pattern: sample up to
``sample_size`` reference figures, VLM-analyze them in batches of
``batch_size`` (map step), then merge the batch analyses into a single
markdown style guide (reduce step). The resulting guide preserves multiple
accepted design options and domain-conditional styling (hex palettes,
line/arrow semantics, shape semantics) rather than averaging everything
into one style.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from pathlib import Path

import structlog

from paperbanana_cn.core.types import ReferenceExample
from paperbanana_cn.core.utils import find_prompt_dir, load_image
from paperbanana_cn.providers.base import VLMProvider

logger = structlog.get_logger()

GUIDE_TYPES = ("methodology", "plot")

_GUIDE_TYPE_LABELS = {
    "methodology": "methodology / architecture diagrams",
    "plot": "statistical plots and charts",
}


class StyleGuideSynthesisError(RuntimeError):
    """Raised when style-guide synthesis cannot proceed (no images, over budget)."""


def _check_budget(vlm: VLMProvider, stage: str) -> None:
    """Abort synthesis if the provider's cost tracker reports budget exhaustion."""
    tracker = getattr(vlm, "cost_tracker", None)
    if tracker is not None and tracker.is_over_budget:
        raise StyleGuideSynthesisError(
            f"Budget exceeded {stage} "
            f"(spent ${tracker.total_cost:.4f} of ${tracker.budget:.4f}). "
            "Increase --budget or reduce --sample-size."
        )


def _load_template(name: str, prompt_dir: str | None) -> str:
    """Load a prompt template from ``{prompt_dir}/guidelines/{name}.txt``."""
    base = Path(prompt_dir) if prompt_dir else Path(find_prompt_dir())
    path = base / "guidelines" / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _fill(template: str, **values: str) -> str:
    """Substitute ``{placeholder}`` tokens without str.format brace pitfalls.

    Batch analyses and captions routinely contain literal braces (LaTeX,
    JSON snippets), so ``str.format`` would raise. Plain replacement keeps
    the established ``{placeholder}`` template convention while staying
    robust to arbitrary corpus text.
    """
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def sample_examples(
    examples: Sequence[ReferenceExample],
    sample_size: int,
    seed: int | None = None,
) -> list[ReferenceExample]:
    """Deterministically sample up to ``sample_size`` examples with existing images.

    Args:
        examples: Candidate reference examples.
        sample_size: Maximum number of examples to keep.
        seed: Seed for ``random.Random`` — same seed and corpus yield the
            same sample.

    Returns:
        Sampled examples in stable (corpus) order.
    """
    eligible = [e for e in examples if e.image_path and Path(e.image_path).exists()]
    if len(eligible) <= sample_size:
        return eligible
    rng = random.Random(seed)
    sampled = rng.sample(eligible, sample_size)
    # Preserve corpus order so batches are stable and reviewable.
    order = {id(e): i for i, e in enumerate(eligible)}
    sampled.sort(key=lambda e: order[id(e)])
    return sampled


def _figure_listing(batch: Sequence[ReferenceExample]) -> str:
    """Describe the images attached to a batch call, in attachment order."""
    lines = []
    for i, example in enumerate(batch, start=1):
        caption = example.caption.strip().replace("\n", " ")
        if len(caption) > 200:
            caption = caption[:197] + "..."
        category = example.category or "uncategorized"
        lines.append(f"{i}. [{example.id}] category: {category} — {caption}")
    return "\n".join(lines)


async def synthesize_style_guide(
    vlm: VLMProvider,
    examples: Sequence[ReferenceExample],
    *,
    guide_type: str = "methodology",
    batch_size: int = 20,
    sample_size: int = 50,
    seed: int | None = None,
    prompt_dir: str | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> str:
    """Synthesize a markdown style guide from a reference figure corpus.

    Map-reduce over the corpus: each batch of figures is analyzed by the VLM
    (palettes, layout, line/shape semantics, typography, per-category
    observations), then a single reduce call merges the batch analyses into
    one guide that preserves multiple accepted options and
    domain-conditional rules.

    Args:
        vlm: VLM provider used for both map and reduce calls.
        examples: Candidate reference examples (only ones whose image file
            exists are used).
        guide_type: ``"methodology"`` or ``"plot"``.
        batch_size: Number of figures per map call.
        sample_size: Maximum number of figures analyzed overall.
        seed: Sampling seed for reproducible corpus subsets.
        prompt_dir: Override for the prompts directory (defaults to
            auto-discovery via :func:`find_prompt_dir`).
        progress_callback: Optional ``callback(message)`` for console progress.

    Returns:
        The synthesized style guide as markdown text.

    Raises:
        ValueError: On invalid ``guide_type``, ``batch_size`` or ``sample_size``.
        StyleGuideSynthesisError: If no examples have images, or the budget
            cap is exhausted mid-run.
    """
    if guide_type not in GUIDE_TYPES:
        raise ValueError(f"guide_type must be one of {GUIDE_TYPES}, got: {guide_type}")
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got: {batch_size}")
    if sample_size < 1:
        raise ValueError(f"sample_size must be >= 1, got: {sample_size}")

    def _progress(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    sampled = sample_examples(examples, sample_size, seed=seed)
    if not sampled:
        raise StyleGuideSynthesisError(
            "No reference examples with existing image files were found. "
            "Run `paperbanana data download` or point --reference-set at a "
            "directory with an index.json and images."
        )

    guide_type_label = _GUIDE_TYPE_LABELS[guide_type]
    batch_template = _load_template("batch_analysis", prompt_dir)
    reduce_template = _load_template("synthesize", prompt_dir)

    batches = [sampled[i : i + batch_size] for i in range(0, len(sampled), batch_size)]
    logger.info(
        "Synthesizing style guide",
        guide_type=guide_type,
        figures=len(sampled),
        batches=len(batches),
        batch_size=batch_size,
    )
    _progress(f"Analyzing {len(sampled)} reference figures in {len(batches)} batch(es)")

    # Map step: one VLM call per batch, with the batch's images attached.
    analyses: list[str] = []
    for batch_num, batch in enumerate(batches, start=1):
        _check_budget(vlm, f"before batch {batch_num}/{len(batches)}")
        images = [load_image(e.image_path) for e in batch]
        prompt = _fill(
            batch_template,
            guide_type_label=guide_type_label,
            figure_count=str(len(batch)),
            figure_listing=_figure_listing(batch),
        )
        _progress(f"Batch {batch_num}/{len(batches)}: analyzing {len(batch)} figures")
        analysis = await vlm.generate(
            prompt=prompt,
            images=images,
            temperature=0.3,
            max_tokens=8192,
        )
        analyses.append(analysis.strip())

    # Reduce step: merge all batch analyses into the final guide.
    _check_budget(vlm, "before final synthesis")
    _progress("Synthesizing final style guide from batch analyses")
    joined = "\n\n".join(
        f"### Batch {i} analysis\n\n{analysis}" for i, analysis in enumerate(analyses, start=1)
    )
    reduce_prompt = _fill(
        reduce_template,
        guide_type_label=guide_type_label,
        batch_count=str(len(analyses)),
        total_figures=str(len(sampled)),
        batch_analyses=joined,
    )
    guide = await vlm.generate(
        prompt=reduce_prompt,
        temperature=0.3,
        max_tokens=8192,
    )

    logger.info("Style guide synthesized", length=len(guide))
    return guide.strip() + "\n"
