"""Polish Agent: improves an existing user-supplied figure via style-guided suggestions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import structlog
from PIL import Image

from paperbanana.agents.base import BaseAgent
from paperbanana.core.utils import load_image, save_image, truncate_text
from paperbanana.providers.base import ImageGenProvider, VLMProvider

logger = structlog.get_logger()

MAX_SUGGESTIONS = 10

# Matches "1. text", "2) text", "- text", "* text", "• text"
_LIST_ITEM_RE = re.compile(r"^\s*(?:\d+[.)]\s+|[-*•]\s+)(.+?)\s*$")
_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*$")


class PolishAgent(BaseAgent):
    """Refines an existing figure in two steps.

    1. ``suggest``: a VLM audits the figure against the venue style guide and
       returns at most :data:`MAX_SUGGESTIONS` concrete, actionable
       presentation improvements.
    2. ``apply``: the suggestions and the original figure are sent to an
       image-edit capable provider (guided edit) which renders the polished
       version while preserving the figure's content.

    Prompt templates live in ``prompts/polish/{suggest,apply}.txt``.
    """

    def __init__(
        self,
        image_gen: ImageGenProvider,
        vlm_provider: VLMProvider,
        prompt_dir: str = "prompts",
        output_dir: str = "outputs",
        prompt_recorder=None,
        image_quality: str = "auto",
    ):
        super().__init__(vlm_provider, prompt_dir, prompt_recorder=prompt_recorder)
        self.image_gen = image_gen
        self.output_dir = Path(output_dir)
        self.image_quality = image_quality

    @property
    def agent_name(self) -> str:
        return "polish"

    @staticmethod
    def supports_guided_edit(image_gen: ImageGenProvider) -> bool:
        """Whether the provider explicitly supports guided image editing."""
        return bool(getattr(image_gen, "supports_image_edit", False))

    def _load_polish_prompt(self, step: str) -> str:
        """Load a polish prompt template (``suggest`` or ``apply``)."""
        path = self.prompt_dir / "polish" / f"{step}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        return path.read_text(encoding="utf-8")

    async def suggest(
        self,
        image: Image.Image,
        style_guide: str,
        max_suggestions: int = MAX_SUGGESTIONS,
        iteration: int = 1,
    ) -> list[str]:
        """Audit *image* against *style_guide* and return actionable suggestions.

        Returns an empty list when the figure already conforms (the VLM
        answers ``NO_SUGGESTIONS``) or when no list items can be parsed.
        """
        template = self._load_polish_prompt("suggest")
        prompt = self.format_prompt(
            template,
            prompt_label=f"polish_suggest_iter_{iteration}",
            style_guide=style_guide,
            max_suggestions=max_suggestions,
        )

        logger.info("Running polish suggest step", iteration=iteration)
        response = await self.vlm.generate(
            prompt=prompt,
            images=[image],
            temperature=0.3,
            max_tokens=2048,
        )
        suggestions = self._parse_suggestions(response, max_suggestions=max_suggestions)
        logger.info("Polish suggestions ready", count=len(suggestions), iteration=iteration)
        return suggestions

    async def apply(
        self,
        image: Image.Image,
        suggestions: list[str],
        output_path: str,
        iteration: int = 1,
        aspect_ratio: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Apply *suggestions* to *image* via a guided edit and save the result.

        The original figure and the numbered suggestions both go to the image
        provider, so the model edits the existing figure instead of
        regenerating from scratch.
        """
        if not self.supports_guided_edit(self.image_gen):
            raise RuntimeError(
                f"Image provider '{getattr(self.image_gen, 'name', 'unknown')}' does not "
                "support guided image editing. "
                "Polish mode requires an image-edit capable provider such as 'google'."
            )

        template = self._load_polish_prompt("apply")
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(suggestions, start=1))
        prompt = self.format_prompt(
            template,
            prompt_label=f"polish_apply_iter_{iteration}",
            suggestions=numbered,
        )

        logger.info("Running polish apply step", iteration=iteration, suggestions=len(suggestions))
        polished = await self.image_gen.generate(
            prompt=prompt,
            images=[image],
            width=image.width,
            height=image.height,
            seed=seed,
            aspect_ratio=aspect_ratio,
            quality=self.image_quality,
        )
        save_image(polished, output_path)
        logger.info("Polished figure saved", path=output_path, iteration=iteration)
        return output_path

    async def run(
        self,
        image_path: str,
        style_guide: str,
        output_path: Optional[str] = None,
        iteration: int = 1,
        aspect_ratio: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> tuple[str, list[str]]:
        """One polish round: suggest improvements, then apply them.

        Returns:
            ``(result_path, suggestions)``. When the VLM finds nothing to
            improve, the original ``image_path`` is returned unchanged with
            an empty suggestion list and the apply step is skipped.
        """
        image = load_image(image_path)
        suggestions = await self.suggest(image, style_guide, iteration=iteration)
        if not suggestions:
            logger.info("No polish suggestions; figure left unchanged", iteration=iteration)
            return image_path, []

        if output_path is None:
            output_path = str(self.output_dir / f"polished_iter_{iteration}.png")
        polished_path = await self.apply(
            image,
            suggestions,
            output_path=output_path,
            iteration=iteration,
            aspect_ratio=aspect_ratio,
            seed=seed,
        )
        return polished_path, suggestions

    @staticmethod
    def _parse_suggestions(
        response: str | None, max_suggestions: int = MAX_SUGGESTIONS
    ) -> list[str]:
        """Parse a VLM response into a list of suggestion strings.

        Handles numbered lists (``1.`` / ``2)``), bulleted lists
        (``-`` / ``*`` / ``•``), and fenced output (code fences are
        stripped). Non-list lines (preamble, prose) are ignored.
        ``NO_SUGGESTIONS`` yields an empty list.
        """
        if not response:
            return []
        if "NO_SUGGESTIONS" in response:
            return []

        suggestions: list[str] = []
        for line in response.splitlines():
            if _FENCE_RE.match(line):
                continue
            match = _LIST_ITEM_RE.match(line)
            if not match:
                continue
            text = match.group(1).replace("**", "").strip()
            if text:
                suggestions.append(text)

        if not suggestions:
            logger.warning(
                "Could not parse any suggestions from VLM response",
                raw_response=truncate_text(response, 500),
            )
        return suggestions[:max_suggestions]
