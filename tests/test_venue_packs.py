"""Tests for user-suppliable venue style packs (resolver, venue.yaml, CLI)."""

from __future__ import annotations

import re

import pytest
import yaml
from typer.testing import CliRunner

from paperbanana_cn.cli import app
from paperbanana_cn.core.config import Settings
from paperbanana_cn.core.pipeline import PaperBananaPipeline
from paperbanana_cn.guidelines.methodology import (
    DEFAULT_METHODOLOGY_GUIDELINES,
    load_methodology_guidelines,
)
from paperbanana_cn.guidelines.plots import DEFAULT_PLOT_GUIDELINES, load_plot_guidelines
from paperbanana_cn.guidelines.venues import (
    UnknownVenueError,
    VenueConfig,
    list_venues,
    load_venue_config,
    resolve_user_venue_dir,
    resolve_venue,
    select_aspect_ratio,
    validate_venue,
)

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _make_pack(root, name, methodology="m-guide", plot="p-guide", config=None):
    """Create a venue pack directory under root."""
    pack = root / name
    pack.mkdir(parents=True)
    if methodology is not None:
        (pack / "methodology_style_guide.md").write_text(methodology)
    if plot is not None:
        (pack / "plot_style_guide.md").write_text(plot)
    if config is not None:
        (pack / "venue.yaml").write_text(config)
    return pack


@pytest.fixture()
def builtin_dir(tmp_path):
    """Built-in guidelines layout: flat neurips files + venue subdirs."""
    base = tmp_path / "builtin"
    base.mkdir()
    (base / "methodology_style_guide.md").write_text("neurips-m")
    (base / "plot_style_guide.md").write_text("neurips-p")
    for venue in ("icml", "acl", "ieee"):
        _make_pack(base, venue, methodology=f"{venue}-m", plot=f"{venue}-p")
    return base


@pytest.fixture()
def user_dir(tmp_path, monkeypatch):
    """Isolated user venue directory (also set as the env default)."""
    d = tmp_path / "user_venues"
    d.mkdir()
    monkeypatch.setenv("PAPERBANANA_VENUE_DIR", str(d))
    return d


# ── User venue directory resolution ──────────────────────────────────


class TestUserVenueDirResolution:
    def test_explicit_dir_wins_over_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PAPERBANANA_VENUE_DIR", str(tmp_path / "from_env"))
        assert resolve_user_venue_dir(tmp_path / "explicit") == tmp_path / "explicit"

    def test_env_var_used_when_no_explicit_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PAPERBANANA_VENUE_DIR", str(tmp_path / "from_env"))
        assert resolve_user_venue_dir() == tmp_path / "from_env"

    def test_default_is_xdg_config_dir(self, monkeypatch):
        monkeypatch.delenv("PAPERBANANA_VENUE_DIR", raising=False)
        # Compare path components, not a string — separators differ on Windows.
        assert resolve_user_venue_dir().parts[-3:] == (".config", "paperbanana", "venues")


# ── Listing & resolution precedence ──────────────────────────────────


class TestListVenues:
    def test_lists_builtin_and_user_with_sources(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab")
        venues = list_venues(builtin_dir=builtin_dir, extra_dir=user_dir)
        assert venues["neurips"].source == "built-in"
        assert venues["icml"].source == "built-in"
        assert venues["mylab"].source == "user"

    def test_builtin_beats_user_on_name_clash(self, builtin_dir, user_dir):
        """Documented precedence: built-in packs win over user packs."""
        _make_pack(user_dir, "icml", methodology="user-icml-m")
        venues = list_venues(builtin_dir=builtin_dir, extra_dir=user_dir)
        assert venues["icml"].source == "built-in"
        assert venues["icml"].dir == builtin_dir / "icml"

    def test_neurips_always_listed_even_without_files(self, tmp_path, user_dir):
        venues = list_venues(builtin_dir=tmp_path / "missing", extra_dir=user_dir)
        assert "neurips" in venues
        assert venues["neurips"].source == "built-in"

    def test_non_pack_dirs_ignored(self, builtin_dir, user_dir):
        (user_dir / "random_junk").mkdir()
        venues = list_venues(builtin_dir=builtin_dir, extra_dir=user_dir)
        assert "random_junk" not in venues


class TestResolveVenue:
    def test_resolves_user_pack(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab", methodology="my-m", plot="my-p")
        pack = resolve_venue("mylab", builtin_dir=builtin_dir, extra_dir=user_dir)
        assert pack.source == "user"
        assert pack.methodology_guide_path.read_text() == "my-m"
        assert pack.plot_guide_path.read_text() == "my-p"

    def test_builtin_beats_user_on_name_clash(self, builtin_dir, user_dir):
        _make_pack(user_dir, "acl", methodology="user-acl-m")
        pack = resolve_venue("acl", builtin_dir=builtin_dir, extra_dir=user_dir)
        assert pack.source == "built-in"
        assert pack.methodology_guide_path.read_text() == "acl-m"

    def test_name_is_case_insensitive(self, builtin_dir, user_dir):
        pack = resolve_venue("  ICML ", builtin_dir=builtin_dir, extra_dir=user_dir)
        assert pack.name == "icml"

    def test_custom_is_reserved(self, builtin_dir, user_dir):
        with pytest.raises(ValueError, match="reserved"):
            resolve_venue("custom", builtin_dir=builtin_dir, extra_dir=user_dir)

    def test_unknown_venue_error_lists_both_sources(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab")
        with pytest.raises(UnknownVenueError) as exc_info:
            resolve_venue("cvpr", builtin_dir=builtin_dir, extra_dir=user_dir)
        message = str(exc_info.value)
        assert "Unknown venue 'cvpr'" in message
        assert "Built-in venues:" in message
        for builtin in ("neurips", "icml", "acl", "ieee"):
            assert builtin in message
        assert "User venues" in message
        assert "mylab" in message

    def test_validate_venue_accepts_none_and_custom(self, builtin_dir, user_dir):
        validate_venue(None, builtin_dir=builtin_dir, extra_dir=user_dir)
        validate_venue("custom", builtin_dir=builtin_dir, extra_dir=user_dir)
        with pytest.raises(UnknownVenueError):
            validate_venue("cvpr", builtin_dir=builtin_dir, extra_dir=user_dir)


# ── venue.yaml parsing ───────────────────────────────────────────────


class TestVenueYaml:
    def test_full_config_parsed(self, user_dir):
        pack_dir = _make_pack(
            user_dir,
            "mylab",
            config=(
                'display_name: "My Lab Style"\n'
                'aspect_ratio: "16:9"\n'
                "fonts:\n  - Helvetica\n  - Arial\n"
            ),
        )
        config = load_venue_config(pack_dir)
        assert config.display_name == "My Lab Style"
        assert config.aspect_ratio == "16:9"
        assert config.fonts == ["Helvetica", "Arial"]

    def test_absent_file_yields_defaults(self, user_dir):
        pack_dir = _make_pack(user_dir, "mylab")
        config = load_venue_config(pack_dir)
        assert config == VenueConfig()
        assert config.display_name is None
        assert config.aspect_ratio is None
        assert config.fonts is None

    def test_empty_file_yields_defaults(self, user_dir):
        pack_dir = _make_pack(user_dir, "mylab", config="")
        assert load_venue_config(pack_dir) == VenueConfig()

    def test_comment_only_file_yields_defaults(self, user_dir):
        pack_dir = _make_pack(user_dir, "mylab", config="# nothing set yet\n")
        assert load_venue_config(pack_dir) == VenueConfig()

    def test_non_mapping_top_level_rejected(self, user_dir):
        pack_dir = _make_pack(user_dir, "mylab", config="- just\n- a\n- list\n")
        with pytest.raises(ValueError, match="expected a mapping"):
            load_venue_config(pack_dir)

    def test_invalid_aspect_ratio_rejected(self, user_dir):
        pack_dir = _make_pack(user_dir, "mylab", config='aspect_ratio: "7:5"\n')
        with pytest.raises(ValueError, match="aspect_ratio must be one of"):
            load_venue_config(pack_dir)

    def test_unknown_keys_ignored(self, user_dir):
        pack_dir = _make_pack(user_dir, "mylab", config="display_name: X\nfuture_field: y\n")
        assert load_venue_config(pack_dir).display_name == "X"

    def test_config_attached_to_resolved_pack(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab", config='aspect_ratio: "21:9"\n')
        pack = resolve_venue("mylab", builtin_dir=builtin_dir, extra_dir=user_dir)
        assert pack.config.aspect_ratio == "21:9"


# ── Guideline loaders with user packs ────────────────────────────────


class TestLoadersWithUserPacks:
    def test_methodology_loaded_from_user_pack(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab", methodology="my lab methodology guide")
        result = load_methodology_guidelines(
            str(builtin_dir), venue="mylab", venue_dir=str(user_dir)
        )
        assert result == "my lab methodology guide"

    def test_plot_loaded_from_user_pack(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab", plot="my lab plot guide")
        result = load_plot_guidelines(str(builtin_dir), venue="mylab", venue_dir=str(user_dir))
        assert result == "my lab plot guide"

    def test_user_pack_found_via_env_var(self, builtin_dir, user_dir):
        """Without an explicit venue_dir, PAPERBANANA_VENUE_DIR is honored."""
        _make_pack(user_dir, "mylab", methodology="env-resolved guide")
        result = load_methodology_guidelines(str(builtin_dir), venue="mylab")
        assert result == "env-resolved guide"

    def test_pack_missing_guide_falls_back_to_defaults_with_warning(self, builtin_dir, user_dir):
        _make_pack(user_dir, "mylab", methodology="only-m", plot=None)
        result = load_plot_guidelines(str(builtin_dir), venue="mylab", venue_dir=str(user_dir))
        assert result == DEFAULT_PLOT_GUIDELINES

    def test_unknown_venue_raises_not_falls_back(self, builtin_dir, user_dir):
        with pytest.raises(UnknownVenueError):
            load_methodology_guidelines(str(builtin_dir), venue="cvpr", venue_dir=str(user_dir))


# ── Aspect ratio defaulting ──────────────────────────────────────────


class TestAspectRatioDefaulting:
    def test_user_ratio_wins(self):
        assert select_aspect_ratio("1:1", "16:9", "4:3") == ("1:1", "user")

    def test_venue_default_used_when_cli_did_not_pass_one(self):
        assert select_aspect_ratio(None, "16:9", "4:3") == ("16:9", "venue")

    def test_planner_used_when_no_user_or_venue_ratio(self):
        assert select_aspect_ratio(None, None, "4:3") == ("4:3", "planner")

    def test_none_when_nothing_set(self):
        assert select_aspect_ratio(None, None, None) == (None, None)

    def test_pipeline_picks_up_venue_pack_and_aspect_ratio(self, builtin_dir, user_dir, tmp_path):
        _make_pack(
            user_dir,
            "mylab",
            methodology="my lab methodology guide",
            plot="my lab plot guide",
            config='aspect_ratio: "16:9"\nfonts:\n  - Helvetica\n',
        )
        settings = Settings(
            venue="mylab",
            venue_dir=str(user_dir),
            guidelines_path=str(builtin_dir),
            output_dir=str(tmp_path / "outputs"),
            save_prompts=False,
        )
        pipeline = PaperBananaPipeline(
            settings=settings,
            vlm_client=object(),
            image_gen_fn=lambda *a, **k: None,
        )
        assert pipeline._venue_pack is not None
        assert pipeline._venue_pack.source == "user"
        assert pipeline._venue_pack.config.aspect_ratio == "16:9"
        assert pipeline._methodology_guidelines.startswith("my lab methodology guide")
        assert "Helvetica" in pipeline._methodology_guidelines
        assert pipeline._plot_guidelines.startswith("my lab plot guide")


# ── CLI: venues list / venues init ───────────────────────────────────


class TestVenuesListCommand:
    def test_lists_builtin_and_user_sources(self, user_dir, monkeypatch):
        _make_pack(user_dir, "mylab", config='display_name: "My Lab"\naspect_ratio: "16:9"\n')
        result = runner.invoke(app, ["venues", "list", "--venue-dir", str(user_dir)])
        out = _strip_ansi(result.output)
        assert result.exit_code == 0
        assert "neurips" in out
        assert "built-in" in out
        assert "mylab" in out
        assert "user" in out
        assert "My Lab" in out
        assert "16:9" in out


class TestVenuesInitCommand:
    def test_scaffolds_pack(self, user_dir):
        result = runner.invoke(app, ["venues", "init", "mylab", "--venue-dir", str(user_dir)])
        out = _strip_ansi(result.output)
        assert result.exit_code == 0, out
        assert "Created venue pack" in out

        pack = user_dir / "mylab"
        methodology = (pack / "methodology_style_guide.md").read_text()
        plot = (pack / "plot_style_guide.md").read_text()
        assert len(methodology) > 100  # seeded from the NeurIPS template
        assert len(plot) > 100
        config_text = (pack / "venue.yaml").read_text()
        assert config_text.startswith("#")  # commented template
        parsed = yaml.safe_load(config_text)
        assert parsed["display_name"] == "MYLAB"

        # The scaffolded pack is immediately usable.
        pack_resolved = resolve_venue("mylab", extra_dir=user_dir)
        assert pack_resolved.source == "user"
        assert load_venue_config(pack) == VenueConfig(display_name="MYLAB")

    def test_seeded_guides_match_defaults_outside_repo(self, user_dir, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["venues", "init", "mylab", "--venue-dir", str(user_dir)])
        assert result.exit_code == 0
        pack = user_dir / "mylab"
        assert (pack / "methodology_style_guide.md").read_text() == DEFAULT_METHODOLOGY_GUIDELINES
        assert (pack / "plot_style_guide.md").read_text() == DEFAULT_PLOT_GUIDELINES

    def test_rejects_builtin_name(self, user_dir):
        result = runner.invoke(app, ["venues", "init", "neurips", "--venue-dir", str(user_dir)])
        out = _strip_ansi(result.output)
        assert result.exit_code == 1
        assert "already exists" in out
        assert not (user_dir / "neurips").exists()

    def test_rejects_existing_user_pack(self, user_dir):
        _make_pack(user_dir, "mylab")
        result = runner.invoke(app, ["venues", "init", "mylab", "--venue-dir", str(user_dir)])
        out = _strip_ansi(result.output)
        assert result.exit_code == 1
        assert "already exists" in out

    def test_rejects_reserved_and_invalid_names(self, user_dir):
        for bad_name in ("custom", "my venue", "../escape"):
            result = runner.invoke(app, ["venues", "init", bad_name, "--venue-dir", str(user_dir)])
            assert result.exit_code == 1, bad_name


# ── CLI: --venue validation on generate/plot ─────────────────────────


class TestCliVenueValidation:
    def test_generate_unknown_venue_lists_available(self, user_dir):
        _make_pack(user_dir, "mylab")
        result = runner.invoke(
            app,
            ["generate", "--venue", "cvpr", "--venue-dir", str(user_dir)],
        )
        out = _strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Unknown venue 'cvpr'" in out
        assert "neurips" in out
        assert "mylab" in out

    def test_plot_unknown_venue_lists_available(self, user_dir):
        result = runner.invoke(
            app,
            [
                "plot",
                "--data",
                "missing.csv",
                "--intent",
                "x",
                "--venue",
                "cvpr",
                "--venue-dir",
                str(user_dir),
            ],
        )
        out = _strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Unknown venue 'cvpr'" in out

    def test_generate_accepts_user_venue_name(self, user_dir):
        """A user pack passes --venue validation (failure later is unrelated)."""
        _make_pack(user_dir, "mylab")
        result = runner.invoke(
            app,
            ["generate", "--venue", "mylab", "--venue-dir", str(user_dir), "--dry-run"],
        )
        out = _strip_ansi(result.output)
        assert "Unknown venue" not in out


class TestBuiltinVenueConfigs:
    """Built-in venues ship venue.yaml with column-aware defaults."""

    def test_two_column_venues_default_to_4_3(self):
        for name in ("icml", "ieee", "acl"):
            pack = resolve_venue(name)
            assert pack.source == "built-in"
            assert pack.config.aspect_ratio == "4:3", f"{name} should default to 4:3"

    def test_font_preferences_loaded(self):
        """Fonts mirror each venue's real body typeface (Times across the board)."""
        assert resolve_venue("icml").config.fonts == ["Times New Roman", "Times"]
        assert resolve_venue("ieee").config.fonts == ["Times New Roman", "Times Roman"]
        assert resolve_venue("acl").config.fonts == ["Times New Roman", "Times Roman"]
