"""Tests for multi-venue style support (--venue flag)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from paperbanana_cn.core.config import Settings
from paperbanana_cn.guidelines.methodology import (
    DEFAULT_METHODOLOGY_GUIDELINES,
    load_methodology_guidelines,
)
from paperbanana_cn.guidelines.plots import (
    DEFAULT_PLOT_GUIDELINES,
    load_plot_guidelines,
)
from paperbanana_cn.guidelines.venues import UnknownVenueError

# ── Settings & Validation ────────────────────────────────────────────


class TestVenueSettings:
    """Venue field on Settings: defaults, validation, YAML loading."""

    def test_default_venue_is_neurips(self):
        settings = Settings()
        assert settings.venue == "neurips"

    @pytest.mark.parametrize("venue", ["neurips", "icml", "acl", "ieee", "custom"])
    def test_valid_venues_accepted(self, venue):
        settings = Settings(venue=venue)
        assert settings.venue == venue

    def test_venue_is_case_insensitive(self):
        settings = Settings(venue="ICML")
        assert settings.venue == "icml"

    def test_arbitrary_venue_names_accepted_and_normalized(self):
        """Venue names are open (user packs); validation happens at resolution."""
        settings = Settings(venue="  MyLab ")
        assert settings.venue == "mylab"

    def test_venue_from_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump({"pipeline": {"venue": "ieee"}}, f)
            path = f.name

        try:
            settings = Settings.from_yaml(path)
            assert settings.venue == "ieee"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_venue_cli_override_beats_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump({"pipeline": {"venue": "neurips"}}, f)
            path = f.name

        try:
            settings = Settings.from_yaml(path, venue="acl")
            assert settings.venue == "acl"
        finally:
            Path(path).unlink(missing_ok=True)


# ── Guideline Loader Resolution ──────────────────────────────────────


@pytest.fixture()
def guidelines_tree(tmp_path):
    """Create a temporary guidelines directory with venue subdirectories."""
    # Flat files (legacy / fallback)
    (tmp_path / "methodology_style_guide.md").write_text("flat-methodology")
    (tmp_path / "plot_style_guide.md").write_text("flat-plot")

    # Venue-specific files
    for venue in ("neurips", "icml", "acl", "ieee"):
        d = tmp_path / venue
        d.mkdir()
        (d / "methodology_style_guide.md").write_text(f"{venue}-methodology")
        (d / "plot_style_guide.md").write_text(f"{venue}-plot")

    return tmp_path


class TestMethodologyGuidelinesLoader:
    """load_methodology_guidelines venue resolution logic."""

    def test_venue_specific_path_resolved(self, guidelines_tree):
        result = load_methodology_guidelines(str(guidelines_tree), venue="icml")
        assert result == "icml-methodology"

    def test_unknown_venue_raises(self, guidelines_tree, monkeypatch, tmp_path):
        """Unknown venues raise instead of silently falling back to flat files."""
        monkeypatch.setenv("PAPERBANANA_VENUE_DIR", str(tmp_path / "empty_user_dir"))
        with pytest.raises(UnknownVenueError, match="Unknown venue 'unknown_venue'"):
            load_methodology_guidelines(str(guidelines_tree), venue="unknown_venue")

    def test_custom_venue_uses_flat_path(self, guidelines_tree):
        """venue='custom' skips venue subdirectory resolution."""
        result = load_methodology_guidelines(str(guidelines_tree), venue="custom")
        assert result == "flat-methodology"

    def test_no_venue_uses_flat_path(self, guidelines_tree):
        result = load_methodology_guidelines(str(guidelines_tree), venue=None)
        assert result == "flat-methodology"

    def test_no_path_returns_hardcoded_default(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result = load_methodology_guidelines(None, venue="neurips")
        assert result == DEFAULT_METHODOLOGY_GUIDELINES

    def test_missing_directory_returns_hardcoded_default(self):
        result = load_methodology_guidelines("/nonexistent/path", venue="neurips")
        assert result == DEFAULT_METHODOLOGY_GUIDELINES

    @pytest.mark.parametrize("venue", ["neurips", "icml", "acl", "ieee"])
    def test_all_venues_resolve(self, guidelines_tree, venue):
        result = load_methodology_guidelines(str(guidelines_tree), venue=venue)
        assert result == f"{venue}-methodology"


class TestPlotGuidelinesLoader:
    """load_plot_guidelines venue resolution logic."""

    def test_venue_specific_path_resolved(self, guidelines_tree):
        result = load_plot_guidelines(str(guidelines_tree), venue="ieee")
        assert result == "ieee-plot"

    def test_unknown_venue_raises(self, guidelines_tree, monkeypatch, tmp_path):
        monkeypatch.setenv("PAPERBANANA_VENUE_DIR", str(tmp_path / "empty_user_dir"))
        with pytest.raises(UnknownVenueError, match="Unknown venue 'unknown_venue'"):
            load_plot_guidelines(str(guidelines_tree), venue="unknown_venue")

    def test_custom_venue_uses_flat_path(self, guidelines_tree):
        result = load_plot_guidelines(str(guidelines_tree), venue="custom")
        assert result == "flat-plot"

    def test_no_venue_uses_flat_path(self, guidelines_tree):
        result = load_plot_guidelines(str(guidelines_tree), venue=None)
        assert result == "flat-plot"

    def test_no_path_returns_hardcoded_default(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result = load_plot_guidelines(None, venue="neurips")
        assert result == DEFAULT_PLOT_GUIDELINES

    def test_missing_directory_returns_hardcoded_default(self):
        result = load_plot_guidelines("/nonexistent/path", venue="neurips")
        assert result == DEFAULT_PLOT_GUIDELINES

    @pytest.mark.parametrize("venue", ["neurips", "icml", "acl", "ieee"])
    def test_all_venues_resolve(self, guidelines_tree, venue):
        result = load_plot_guidelines(str(guidelines_tree), venue=venue)
        assert result == f"{venue}-plot"


# ── Shipped Guideline Files ──────────────────────────────────────────


class TestShippedGuidelineFiles:
    """Verify that all venue guideline files actually exist in data/guidelines/."""

    GUIDELINES_DIR = Path(__file__).resolve().parent.parent / "data" / "guidelines"

    @pytest.mark.parametrize("venue", ["icml", "acl", "ieee"])
    def test_methodology_guide_exists(self, venue):
        path = self.GUIDELINES_DIR / venue / "methodology_style_guide.md"
        assert path.exists(), f"Missing: {path}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 100, f"Guideline file looks too short: {path}"

    @pytest.mark.parametrize("venue", ["icml", "acl", "ieee"])
    def test_plot_guide_exists(self, venue):
        path = self.GUIDELINES_DIR / venue / "plot_style_guide.md"
        assert path.exists(), f"Missing: {path}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 100, f"Guideline file looks too short: {path}"

    def test_neurips_served_by_flat_files(self):
        """NeurIPS uses the flat files directly — no subdirectory needed."""
        assert (self.GUIDELINES_DIR / "methodology_style_guide.md").exists()
        assert (self.GUIDELINES_DIR / "plot_style_guide.md").exists()
        assert not (self.GUIDELINES_DIR / "neurips").exists()


# ── Backward Compatibility ───────────────────────────────────────────


class TestBackwardCompatibility:
    """Existing behavior must not break when venue is not specified."""

    def test_loader_without_venue_param_still_works(self, guidelines_tree):
        """Callers that don't pass venue at all get flat-path behavior."""
        result = load_methodology_guidelines(str(guidelines_tree))
        assert result == "flat-methodology"

    def test_settings_without_venue_defaults_to_neurips(self):
        settings = Settings()
        assert settings.venue == "neurips"

    def test_flat_path_config_still_works(self, tmp_path):
        """A user with guidelines_path pointing to a flat directory still works."""
        (tmp_path / "methodology_style_guide.md").write_text("my custom guide")
        result = load_methodology_guidelines(str(tmp_path), venue="custom")
        assert result == "my custom guide"
