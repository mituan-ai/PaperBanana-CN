"""Small Gradio 6.20 locale bridge for the custom Studio toolbar."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_GRADIO_VERSION = "6.20.0"


def _i18n_asset_name(gradio_module) -> str:
    """Return the version-locked frontend module that owns Gradio's locale store."""
    version = getattr(gradio_module, "__version__", "")
    if version != SUPPORTED_GRADIO_VERSION:
        raise RuntimeError(
            "PaperBanana-CN Studio language switching requires "
            f"gradio=={SUPPORTED_GRADIO_VERSION}; found {version or 'unknown'}"
        )
    assets = Path(gradio_module.__file__).parent / "templates" / "frontend" / "assets"
    matches = sorted(assets.glob("i18n-*.js"))
    if len(matches) != 1:
        raise RuntimeError("Could not identify the installed Gradio i18n frontend module")
    source = matches[0].read_text(encoding="utf-8")
    if "Q," not in source and "Q as" not in source:
        raise RuntimeError(
            "Installed Gradio i18n module does not expose the expected locale setter"
        )
    return matches[0].name


def locale_switch_js(gradio_module, *, initial: bool) -> str:
    """Build a client callback that uses the same locale setter as Gradio Settings."""
    asset = _i18n_asset_name(gradio_module)
    preferred = "localStorage.getItem('paperbanana-cn.locale') || locale" if initial else "locale"
    mark_ready = (
        "" if initial else "document.documentElement.dataset.paperbananaLocaleReady = 'true';"
    )
    return f"""
async (locale) => {{
  const selected = {preferred};
  try {{
    const moduleScript = [...document.querySelectorAll('script[type="module"][src]')]
      .find((script) => script.src.includes('/assets/index-'));
    if (!moduleScript) throw new Error('Gradio module script was not found');
    const i18n = await import(new URL('{asset}', moduleScript.src).href);
    if (typeof i18n.Q !== 'function') throw new Error('Gradio locale setter is unavailable');
    await i18n.Q(selected);
    localStorage.setItem('paperbanana-cn.locale', selected);
    document.documentElement.dataset.paperbananaLocale = selected;
  }} catch (error) {{
    console.error('PaperBanana-CN could not switch the interface language', error);
  }} finally {{
    {mark_ready}
  }}
  return selected;
}}
""".strip()


def locale_ready_js() -> str:
    """Reveal the shell only after all initial persisted state has loaded."""
    return """() => {
  document.documentElement.dataset.paperbananaLocaleReady = 'true';
}"""
