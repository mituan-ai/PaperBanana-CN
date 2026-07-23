"""Stable paths for Studio-owned brand assets."""

from pathlib import Path

STUDIO_ASSET_DIR = Path(__file__).with_name("assets")
BRAND_LOGO_FILENAME = "paperbanana-cn-logo.jpg"
BRAND_LOGO_PATH = STUDIO_ASSET_DIR / BRAND_LOGO_FILENAME
STUDIO_ASSET_MOUNT = "/paperbanana-assets"
BRAND_LOGO_URL = f".{STUDIO_ASSET_MOUNT}/{BRAND_LOGO_FILENAME}"
