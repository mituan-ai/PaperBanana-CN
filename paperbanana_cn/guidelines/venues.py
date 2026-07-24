"""Venue style pack resolution.

A *venue style pack* is a directory containing:

- ``methodology_style_guide.md`` — style guide for methodology diagrams
- ``plot_style_guide.md`` — style guide for statistical plots
- ``venue.yaml`` (optional) — venue metadata, see :class:`VenueConfig`

Packs are resolved from two sources, in order:

1. **Built-in** packs shipped with PaperBanana under ``data/guidelines/``.
   The ``neurips`` pack is special-cased: its guides live as flat files
   directly under ``data/guidelines/`` and it is always available (falling
   back to the baked-in default guidelines if the files are missing).
2. **User** packs from a user venue directory, resolved as:
   an explicit ``--venue-dir`` flag / ``extra_dir`` argument, else the
   ``PAPERBANANA_VENUE_DIR`` environment variable, else
   ``~/.config/paperbanana-cn/venues``.

On a name clash, the **built-in pack wins** — user packs cannot shadow
built-in venues. The name ``custom`` is reserved (it bypasses venue
resolution entirely and loads flat files from the guidelines path).

``venue.yaml`` schema (all fields optional)::

    display_name: "NeurIPS 2025"   # human-readable name for listings
    aspect_ratio: "16:9"           # default --aspect-ratio for this venue
    fonts:                         # preferred font families, appended as a
      - "Helvetica"                # note to the venue's style guides
      - "Arial"
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import structlog
import yaml
from pydantic import BaseModel, field_validator

from paperbanana_cn.core.types import SUPPORTED_ASPECT_RATIOS

logger = structlog.get_logger()

METHODOLOGY_GUIDE_FILENAME = "methodology_style_guide.md"
PLOT_GUIDE_FILENAME = "plot_style_guide.md"
VENUE_CONFIG_FILENAME = "venue.yaml"

DEFAULT_BUILTIN_GUIDELINES_DIR = "data/guidelines"
VENUE_DIR_ENV_VAR = "PAPERBANANA_VENUE_DIR"
DEFAULT_USER_VENUE_DIR = Path.home() / ".config" / "paperbanana-cn" / "venues"

#: Reserved venue names that never resolve to a pack directory.
RESERVED_VENUE_NAMES = frozenset({"custom"})

VenueSource = Literal["built-in", "user"]


class UnknownVenueError(ValueError):
    """Raised when a venue name does not resolve to any style pack."""

    def __init__(self, name: str, builtin_names: list[str], user_names: list[str], user_dir: Path):
        self.name = name
        self.builtin_names = builtin_names
        self.user_names = user_names
        self.user_dir = user_dir
        builtin_part = ", ".join(builtin_names) if builtin_names else "(none)"
        user_part = ", ".join(user_names) if user_names else "(none)"
        super().__init__(
            f"Unknown venue '{name}'. "
            f"Built-in venues: {builtin_part}. "
            f"User venues in {user_dir}: {user_part}. "
            "Run 'paperbanana-cn venues list' to see all packs, or "
            "'paperbanana-cn venues init <name>' to scaffold a new one."
        )


class VenueConfig(BaseModel):
    """Optional venue metadata parsed from ``venue.yaml``.

    All fields are optional; an absent or empty ``venue.yaml`` yields the
    defaults below.
    """

    display_name: Optional[str] = None
    aspect_ratio: Optional[str] = None
    fonts: Optional[list[str]] = None

    model_config = {"extra": "ignore"}

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: Optional[str]) -> Optional[str]:
        """Ensure aspect_ratio, when provided, is one of the supported values."""
        if v is None:
            return v
        if v not in SUPPORTED_ASPECT_RATIOS:
            supported = ", ".join(sorted(SUPPORTED_ASPECT_RATIOS))
            raise ValueError(f"venue.yaml aspect_ratio must be one of: {supported}. Got: {v}")
        return v


class VenuePack(BaseModel):
    """A resolved venue style pack."""

    name: str
    dir: Path
    source: VenueSource
    methodology_guide_path: Optional[Path] = None
    plot_guide_path: Optional[Path] = None
    config: VenueConfig = VenueConfig()


class VenueInfo(BaseModel):
    """A venue listing entry (name, location, and source)."""

    name: str
    dir: Path
    source: VenueSource


def resolve_user_venue_dir(extra_dir: str | Path | None = None) -> Path:
    """Resolve the user venue directory.

    Precedence: explicit ``extra_dir`` > ``PAPERBANANA_VENUE_DIR`` env var >
    ``~/.config/paperbanana-cn/venues``.
    """
    if extra_dir:
        return Path(extra_dir).expanduser()
    env_dir = os.environ.get(VENUE_DIR_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser()
    return DEFAULT_USER_VENUE_DIR


def _is_pack_dir(path: Path) -> bool:
    """A directory qualifies as a venue pack if it has at least one pack file."""
    return (
        (path / METHODOLOGY_GUIDE_FILENAME).is_file()
        or (path / PLOT_GUIDE_FILENAME).is_file()
        or (path / VENUE_CONFIG_FILENAME).is_file()
    )


def _scan_pack_dirs(root: Path) -> dict[str, Path]:
    """Map venue name -> pack directory for all pack subdirectories of root."""
    packs: dict[str, Path] = {}
    if not root.is_dir():
        return packs
    for child in sorted(root.iterdir()):
        name = child.name.lower()
        if child.is_dir() and name not in RESERVED_VENUE_NAMES and _is_pack_dir(child):
            packs.setdefault(name, child)
    return packs


def _builtin_packs(builtin_dir: str | Path | None) -> dict[str, Path]:
    """Built-in packs: venue subdirectories plus the implicit flat neurips pack."""
    base = Path(builtin_dir) if builtin_dir else Path(DEFAULT_BUILTIN_GUIDELINES_DIR)
    packs = _scan_pack_dirs(base)
    # NeurIPS is the project default and is served by the flat files directly
    # under the guidelines dir. It is always available: when the files are
    # missing the loaders fall back to the baked-in default guidelines.
    packs.setdefault("neurips", base)
    return packs


def list_venues(
    builtin_dir: str | Path | None = None,
    extra_dir: str | Path | None = None,
) -> dict[str, VenueInfo]:
    """List all available venue packs from both sources.

    On a name clash, the built-in pack wins (user packs cannot shadow
    built-in venues).

    Args:
        builtin_dir: Built-in guidelines directory (default: ``data/guidelines``).
        extra_dir: User venue directory override (default: env var, then
            ``~/.config/paperbanana-cn/venues``).

    Returns:
        Mapping of venue name to :class:`VenueInfo`, sorted by name.
    """
    venues: dict[str, VenueInfo] = {}
    for name, path in _scan_pack_dirs(resolve_user_venue_dir(extra_dir)).items():
        venues[name] = VenueInfo(name=name, dir=path, source="user")
    for name, path in _builtin_packs(builtin_dir).items():
        venues[name] = VenueInfo(name=name, dir=path, source="built-in")
    return dict(sorted(venues.items()))


def load_venue_config(pack_dir: Path) -> VenueConfig:
    """Parse ``venue.yaml`` from a pack directory.

    An absent or empty file yields default (all-None) config. A file whose
    top level is not a mapping raises ``ValueError``.
    """
    config_path = pack_dir / VENUE_CONFIG_FILENAME
    if not config_path.is_file():
        return VenueConfig()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if raw is None:
        return VenueConfig()
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid venue.yaml (expected a mapping at top level): {config_path}")
    return VenueConfig(**raw)


def resolve_venue(
    name: str,
    builtin_dir: str | Path | None = None,
    extra_dir: str | Path | None = None,
) -> VenuePack:
    """Resolve a venue name to a style pack.

    Built-in packs are checked first, then user packs. Unknown names raise
    :class:`UnknownVenueError` listing the venues available from both sources.

    Args:
        name: Venue name (case-insensitive). ``custom`` is reserved and not
            resolvable.
        builtin_dir: Built-in guidelines directory (default: ``data/guidelines``).
        extra_dir: User venue directory override (default: env var, then
            ``~/.config/paperbanana-cn/venues``).

    Returns:
        The resolved :class:`VenuePack`.
    """
    normalized = name.strip().lower()
    if normalized in RESERVED_VENUE_NAMES:
        raise ValueError(
            f"Venue name '{normalized}' is reserved: 'custom' bypasses venue resolution "
            "and loads flat guideline files from the guidelines path."
        )

    builtins = _builtin_packs(builtin_dir)
    user_dir = resolve_user_venue_dir(extra_dir)
    users = _scan_pack_dirs(user_dir)

    if normalized in builtins:
        pack_dir = builtins[normalized]
        source: VenueSource = "built-in"
        if normalized in users:
            logger.warning(
                "User venue pack is shadowed by a built-in venue of the same name",
                venue=normalized,
                user_pack=str(users[normalized]),
            )
    elif normalized in users:
        pack_dir = users[normalized]
        source = "user"
    else:
        raise UnknownVenueError(
            normalized,
            builtin_names=sorted(builtins),
            user_names=sorted(users),
            user_dir=user_dir,
        )

    methodology_path = pack_dir / METHODOLOGY_GUIDE_FILENAME
    plot_path = pack_dir / PLOT_GUIDE_FILENAME
    return VenuePack(
        name=normalized,
        dir=pack_dir,
        source=source,
        methodology_guide_path=methodology_path if methodology_path.is_file() else None,
        plot_guide_path=plot_path if plot_path.is_file() else None,
        config=load_venue_config(pack_dir),
    )


def validate_venue(
    venue: str | None,
    builtin_dir: str | Path | None = None,
    extra_dir: str | Path | None = None,
) -> None:
    """Validate a venue name, raising :class:`UnknownVenueError` if unknown.

    ``None`` and ``custom`` are accepted without resolution.
    """
    if not venue or venue.strip().lower() in RESERVED_VENUE_NAMES:
        return
    resolve_venue(venue, builtin_dir=builtin_dir, extra_dir=extra_dir)


def select_aspect_ratio(
    user_ratio: str | None,
    venue_ratio: str | None,
    planner_ratio: str | None,
) -> tuple[str | None, str | None]:
    """Pick the effective aspect ratio and its source.

    Priority: user-specified > venue default (from ``venue.yaml``) >
    planner-recommended.

    Returns:
        Tuple of ``(effective_ratio, source)`` where source is one of
        ``"user"``, ``"venue"``, ``"planner"`` or ``None``.
    """
    if user_ratio:
        return user_ratio, "user"
    if venue_ratio:
        return venue_ratio, "venue"
    if planner_ratio:
        return planner_ratio, "planner"
    return None, None
