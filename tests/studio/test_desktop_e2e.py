"""Browser-level regression tests for the desktop Studio contract."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
import uvicorn
from PIL import Image

from paperbanana.connections.manager import ConnectionManager
from paperbanana.connections.models import ConnectionProfile, ConnectionRole
from paperbanana.studio.models import WORKFLOW_SPECS

playwright = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.studio_e2e


@dataclass
class StudioProbe:
    methodology_calls: list[dict[str, Any]] = field(default_factory=list)
    plot_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RunningStudio:
    url: str
    manager: ConnectionManager
    probe: StudioProbe
    secret_values: tuple[str, str]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def running_studio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from paperbanana.studio import app as app_module
    from paperbanana.studio.pages import generate as generate_page

    # Gradio probes its own startup endpoint; keep that request off host proxies.
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")

    manager = ConnectionManager(
        tmp_path / "config" / "connections.json",
        tmp_path / "data" / "secrets.json",
    )
    vlm_secret = "browser-vlm-secret"
    image_secret = "browser-image-secret"
    vlm = ConnectionProfile(
        id="test-vlm",
        name="Research VLM",
        role=ConnectionRole.VLM,
        provider="openai",
        base_url="https://vlm.invalid/v1",
        model="vlm-test-model",
    )
    image = ConnectionProfile(
        id="test-image",
        name="Research Image",
        role=ConnectionRole.IMAGE,
        provider="openai_imagen",
        base_url="https://image.invalid/v1",
        model="image-test-model",
        image_size_mode="explicit_pixels",
    )
    manager.save_profile(vlm, api_key=vlm_secret)
    manager.save_profile(image, api_key=image_secret)
    manager.save_preferences(locale="zh-CN", aspect_ratio="16:9", output_resolution="2k")

    result_image = tmp_path / "fake-result.png"
    Image.new("RGB", (640, 360), "white").save(result_image)
    probe = StudioProbe()

    def fake_run_methodology(settings, source_context, caption, aspect_ratio, **kwargs):
        time.sleep(0.25)
        probe.methodology_calls.append(
            {
                "settings": settings,
                "source_context": source_context,
                "caption": caption,
                "aspect_ratio": aspect_ratio,
                "kwargs": kwargs,
            }
        )
        if source_context == "FAIL":
            return "FAKE_FAILED", None, [], "fake backend failure"
        return "FAKE_DONE", str(result_image), [(str(result_image), "iteration 1")], ""

    def fake_run_plot(settings, data_path, intent, aspect_ratio, **kwargs):
        probe.plot_calls.append(
            {
                "settings": settings,
                "data_path": data_path,
                "intent": intent,
                "aspect_ratio": aspect_ratio,
                "kwargs": kwargs,
            }
        )
        return "FAKE_PLOT_DONE", str(result_image), [], ""

    monkeypatch.setattr(generate_page, "run_methodology", fake_run_methodology)
    monkeypatch.setattr(generate_page, "run_plot", fake_run_plot)
    port = _free_port()
    server_app = app_module.build_studio_server_app(
        default_output_dir=str(tmp_path / "outputs"),
        connection_manager=manager,
        server_port=port,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            server_app,
            host="127.0.0.1",
            port=port,
            log_level="error",
        )
    )
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started
    try:
        yield RunningStudio(
            url=f"http://127.0.0.1:{port}",
            manager=manager,
            probe=probe,
            secret_values=(vlm_secret, image_secret),
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.fixture
def browser_page():
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            yield page
        finally:
            browser.close()


def _control(page, elem_id: str):
    return page.locator(f"#{elem_id}").locator("textarea, input").first


def _open_studio(page, url: str, expected_title: str = "科研方法图") -> None:
    page.goto(url, wait_until="domcontentloaded")
    page.locator("#studio-workflows").wait_for(state="visible")
    page.locator("#studio-brand").get_by_text("PaperBanana-CN", exact=True).wait_for(
        state="visible"
    )
    playwright.expect(page.locator("#current-page-title")).to_contain_text(expected_title)


def _assert_no_secret_leaks(page, secrets: tuple[str, ...]) -> None:
    browser_output = "\n".join(message.text for message in page.console_messages())
    page_output = f"{page.locator('body').inner_text()}\n{page.content()}"
    for secret in secrets:
        assert secret not in page_output
        assert secret not in browser_output


def test_studio_passes_saved_connections_to_generation(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)

    assert "PaperBanana" in page.locator("body").inner_text()
    _assert_no_secret_leaks(page, running_studio.secret_values)

    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    _control(page, "connection-vlm-model").fill("unsaved-model")
    page.locator("#nav-diagram").click()
    page.locator("#page-diagram").wait_for(state="visible")
    _control(page, "diagram-context").fill("A three-stage scientific workflow")
    _control(page, "diagram-caption").fill("Overview of the proposed method")
    page.locator("#diagram-generate").click()
    playwright.expect(page.locator("#diagram-generate")).to_be_disabled()
    playwright.expect(_control(page, "diagram-progress")).to_have_value("FAKE_DONE")
    playwright.expect(page.locator("#diagram-generate")).to_be_enabled()
    playwright.expect(_control(page, "diagram-progress")).not_to_be_visible()

    assert len(running_studio.probe.methodology_calls) == 1
    call = running_studio.probe.methodology_calls[0]
    assert call["source_context"] == "A three-stage scientific workflow"
    assert call["caption"] == "Overview of the proposed method"
    assert call["aspect_ratio"] == "16:9"
    assert call["settings"].effective_vlm_model == "vlm-test-model"
    assert call["settings"].effective_image_model == "image-test-model"
    assert call["settings"].output_resolution == "2k"


def test_connection_editor_persists_and_does_not_refill_key(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.locator("#connection-vlm-new").click()
    playwright.expect(_control(page, "connection-vlm-name")).to_have_value("")
    _control(page, "connection-vlm-name").fill("Secondary VLM")
    _control(page, "connection-vlm-url").fill("https://secondary.invalid/v1")
    _control(page, "connection-vlm-model").fill("secondary-model")
    _control(page, "connection-vlm-api-key").fill("new-browser-secret")
    page.locator("#connection-vlm-save").click()

    playwright.expect(_control(page, "connection-vlm-api-key")).to_have_value("")
    config = running_studio.manager.load()
    assert config.profile(config.active_vlm_profile_id, ConnectionRole.VLM).name == "Research VLM"
    page.locator("#connection-vlm-save-use").click()
    playwright.expect(page.locator("#connection-vlm-status")).to_contain_text("Secondary VLM")
    config = running_studio.manager.load()
    assert config.profile(config.active_vlm_profile_id, ConnectionRole.VLM).name == "Secondary VLM"
    _assert_no_secret_leaks(page, ("new-browser-secret", *running_studio.secret_values))

    page.locator("#nav-diagram").click()
    page.locator("#page-diagram").wait_for(state="visible")
    _control(page, "diagram-context").fill("Use the newly activated connection")
    _control(page, "diagram-caption").fill("Connection state test")
    page.locator("#diagram-generate").click()
    playwright.expect(_control(page, "diagram-progress")).to_have_value("FAKE_DONE")
    settings = running_studio.probe.methodology_calls[-1]["settings"]
    assert settings.effective_vlm_model == "secondary-model"


def test_connection_copy_delete_clear_and_paid_confirmation_are_explicit(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")

    page.get_by_role("tab", name="图像生成连接").click()
    page.locator("#connection-image-test").click()
    paid_confirmation = page.locator("#connection-image-paid-confirm").last
    playwright.expect(paid_confirmation).to_be_visible()
    playwright.expect(page.locator("#connection-image-status")).to_contain_text("配置校验通过")
    paid_confirmation.get_by_role("button", name="取消").click()
    playwright.expect(paid_confirmation).not_to_be_visible()

    page.locator("#connection-image-copy").click()
    playwright.expect(page.locator("#connection-image-status")).to_contain_text("已复制")
    assert (
        len(
            [
                item
                for item in running_studio.manager.load().profiles
                if item.role == ConnectionRole.IMAGE
            ]
        )
        == 2
    )
    page.locator("#connection-image-delete").click()
    page.locator("#connection-image-delete-confirm").get_by_role("button", name="确认删除").click()
    playwright.expect(page.locator("#connection-image-status")).to_contain_text("连接已删除")
    assert (
        len(
            [
                item
                for item in running_studio.manager.load().profiles
                if item.role == ConnectionRole.IMAGE
            ]
        )
        == 1
    )

    page.get_by_role("tab", name="视觉语言模型连接").click()
    page.locator("#connection-vlm-clear").click()
    page.locator("#connection-vlm-clear-confirm").get_by_role("button", name="确认清除").click()
    playwright.expect(page.locator("#connection-vlm-status")).to_contain_text("已清除 API Key")
    stored = running_studio.manager.load().profile("test-vlm", ConnectionRole.VLM)
    assert stored.credential_ref is None
    _assert_no_secret_leaks(page, running_studio.secret_values)


def test_validation_and_backend_failure_keep_inputs_and_expand_real_log(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)

    page.locator("#diagram-generate").click()
    playwright.expect(page.locator("#diagram-validation")).to_contain_text("不能为空")
    assert running_studio.probe.methodology_calls == []

    _control(page, "diagram-context").fill("FAIL")
    _control(page, "diagram-caption").fill("Failure test")
    page.locator("#diagram-generate").click()
    playwright.expect(_control(page, "diagram-progress")).to_have_value("FAKE_FAILED")
    playwright.expect(_control(page, "diagram-progress")).to_be_visible()
    playwright.expect(_control(page, "diagram-context")).to_have_value("FAIL")
    assert len(running_studio.probe.methodology_calls) == 1


def test_single_page_locale_switches_without_settings_dialog_or_navigation(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    file_upload = page.locator(
        '#diagram-context-file button[aria-label="Click to upload or drop files"]'
    )
    assert (
        file_upload.evaluate(
            "element => getComputedStyle(element.firstElementChild, '::after').content"
        )
        == '"点击选择或拖放文件"'
    )
    for label in [
        "科研方法图",
        "统计图",
        "质量评估",
        "继续运行",
        "批处理",
        "全文编排",
        "多图组合",
        "参数扫描",
        "运行记录",
    ]:
        playwright.expect(page.get_by_text(label, exact=True).first).to_be_attached()

    for page_id in [
        "plot",
        "continue",
        "evaluate",
        "orchestrate",
        "batch",
        "sweep",
        "composite",
        "runs",
        "settings",
        "diagram",
    ]:
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")

    assert page.locator('[role="dialog"]').count() == 0
    assert page.locator("footer").count() == 0
    original_url = page.url
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.get_by_role("tab", name="常规设置").click()
    page.locator("#studio-locale-switch").get_by_label("English", exact=True).check()
    playwright.expect(page.locator("#current-page-title")).to_contain_text("Settings")
    assert page.url == original_url
    assert page.locator('[role="dialog"]').count() == 0
    assert page.get_by_text("Settings", exact=True).count() == 2
    assert running_studio.manager.load().locale == "en"
    page.locator("#nav-orchestrate").click()
    page.locator("#page-orchestrate").wait_for(state="visible")
    for label in (
        "Orchestration plan",
        "Figure package",
        "Orchestration log",
    ):
        playwright.expect(page.get_by_role("tab", name=label, exact=True)).to_be_visible()
    page.locator("#nav-runs").click()
    page.locator("#page-runs").wait_for(state="visible")
    for label in (
        "Run browser",
        "Run comparison",
        "Run metadata",
        "Original run input",
    ):
        playwright.expect(page.get_by_role("tab", name=label, exact=True)).to_be_visible()
    page.locator("#nav-diagram").click()
    page.locator("#page-diagram").wait_for(state="visible")
    page.locator("#diagram-generate").click()
    playwright.expect(page.locator("#diagram-validation")).to_contain_text("Context is empty.")
    _control(page, "diagram-context").fill("English locale callback")
    _control(page, "diagram-caption").fill("Locale test")
    page.locator("#diagram-generate").click()
    playwright.expect(_control(page, "diagram-progress")).to_have_value("FAKE_DONE")
    assert running_studio.probe.methodology_calls[-1]["kwargs"]["locale"] == "en"
    page.reload(wait_until="domcontentloaded")
    page.locator("#studio-workflows").wait_for(state="visible")
    playwright.expect(page.locator("#current-page-title")).to_contain_text("Diagram")
    assert page.url == original_url

    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.get_by_role("tab", name="General").click()
    page.locator("#studio-locale-switch").get_by_label("中文", exact=True).check()
    playwright.expect(page.locator("#current-page-title")).to_contain_text("设置")
    page.locator("#nav-orchestrate").click()
    page.locator("#page-orchestrate").wait_for(state="visible")
    for label in (
        "编排计划预览",
        "图包清单预览",
        "全文编排日志",
    ):
        playwright.expect(page.get_by_role("tab", name=label, exact=True)).to_be_visible()
    page.locator("#nav-runs").click()
    page.locator("#page-runs").wait_for(state="visible")
    for label in (
        "运行浏览",
        "运行对比",
        "运行元数据",
        "原始运行输入",
    ):
        playwright.expect(page.get_by_role("tab", name=label, exact=True)).to_be_visible()
    assert page.url == original_url
    assert page.locator('[role="dialog"]').count() == 0
    assert page.locator("footer").count() == 0


def test_header_contains_only_page_context_and_settings_owns_configuration(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    header = page.locator("#studio-header")
    playwright.expect(header.locator("#current-page-title")).to_be_visible()
    assert header.locator("#active-vlm-connection").count() == 0
    assert header.locator("#active-image-connection").count() == 0
    assert header.locator("#studio-locale-switch").count() == 0

    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    playwright.expect(page.get_by_role("tab", name="视觉语言模型连接")).to_be_visible()
    playwright.expect(page.get_by_role("tab", name="图像生成连接")).to_be_visible()
    page.get_by_role("tab", name="常规设置").click()
    playwright.expect(page.locator("#studio-locale-switch")).to_be_visible()
    locale_box = page.locator("#studio-locale-switch").bounding_box()
    assert locale_box
    assert 260 <= locale_box["width"] <= 300
    assert 34 <= locale_box["height"] <= 48
    assert "顶部连接选择器" not in page.locator("#page-settings").inner_text()


def test_segmented_controls_have_one_visual_affordance(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)
    controls = [
        ("settings", "#studio-locale-switch"),
        ("composite", "#composite-label-position"),
        ("evaluate", "#evaluate-target"),
        ("batch", "#batch-type"),
    ]
    for page_id, selector in controls:
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")
        if page_id == "settings":
            page.get_by_role("tab", name="常规设置").click()
        metrics = page.locator(selector).evaluate(
            """root => {
              const inputs = [...root.querySelectorAll('input[type="radio"]')];
              const labels = inputs.map((input) => input.closest('label'));
              const selected = labels.find((label) => label.querySelector('input:checked'));
              const idle = labels.find((label) => !label.querySelector('input:checked'));
              return {
                display: getComputedStyle(
                  root.querySelector(':scope > .wrap:not([data-testid="status-tracker"])')
                ).display,
                inputs: inputs.map((input) => {
                  const rect = input.getBoundingClientRect();
                  const labelRect = input.closest('label').getBoundingClientRect();
                  const textRect = input.nextElementSibling.getBoundingClientRect();
                  const style = getComputedStyle(input);
                  return {
                    opacity: Number.parseFloat(style.opacity),
                    position: style.position,
                    pointerEvents: style.pointerEvents,
                    width: rect.width,
                    height: rect.height,
                    labelWidth: labelRect.width,
                    labelHeight: labelRect.height,
                    textCenterOffset:
                      textRect.left + textRect.width / 2 -
                      (labelRect.left + labelRect.width / 2),
                  };
                }),
                labelHeights: labels.map((label) => label.getBoundingClientRect().height),
                selectedBackground: getComputedStyle(selected).backgroundColor,
                idleBackground: getComputedStyle(idle).backgroundColor,
              };
            }"""
        )
        assert metrics["display"] == "grid"
        assert len(metrics["inputs"]) == 2
        assert all(item["opacity"] == 0 for item in metrics["inputs"])
        assert all(item["position"] == "absolute" for item in metrics["inputs"])
        assert all(item["pointerEvents"] == "auto" for item in metrics["inputs"])
        assert all(
            abs(item["width"] - item["labelWidth"]) <= 1
            and abs(item["height"] - item["labelHeight"]) <= 1
            for item in metrics["inputs"]
        ), metrics
        assert all(abs(item["textCenterOffset"]) <= 1 for item in metrics["inputs"]), metrics
        assert max(metrics["labelHeights"]) - min(metrics["labelHeights"]) <= 1
        assert metrics["selectedBackground"] != metrics["idleBackground"]

        target = page.locator(f"{selector} input[type='radio']:not(:checked)").first
        if page_id == "settings":
            target = page.locator(f"{selector} input[type='radio']:checked")
        target_value = target.get_attribute("value")
        target = page.locator(f'{selector} input[type="radio"][value="{target_value}"]')
        target_box = target.bounding_box()
        assert target_box
        hit = page.evaluate(
            "([x, y]) => document.elementFromPoint(x, y).tagName",
            [target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2],
        )
        assert hit == "INPUT"
        page.mouse.click(
            target_box["x"] + target_box["width"] / 2,
            target_box["y"] + target_box["height"] / 2,
        )
        playwright.expect(target).to_be_checked()

    page.locator("#nav-settings").click()
    page.get_by_role("tab", name="视觉语言模型连接").click()
    profile_radio = page.locator("#connection-vlm-selector input[type='radio']").first
    profile_metrics = profile_radio.evaluate(
        """input => {
          const rect = input.getBoundingClientRect();
          return {opacity: getComputedStyle(input).opacity, width: rect.width, height: rect.height};
        }"""
    )
    assert profile_metrics["opacity"] == "1"
    assert profile_metrics["width"] >= 12
    assert profile_metrics["height"] >= 12


def test_segmented_control_and_dropdown_share_one_field_grid(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    page.locator("#nav-composite").click()
    page.locator("#page-composite").wait_for(state="visible")

    geometry = page.evaluate(
        """() => {
          const rect = (element) => {
            const box = element.getBoundingClientRect();
            return {
              top: box.top,
              bottom: box.bottom,
              width: box.width,
              height: box.height,
            };
          };
          const dropdown = document.querySelector('#composite-layout');
          const segmented = document.querySelector('#composite-label-position');
          return {
            dropdown: {
              root: rect(dropdown),
              label: rect(dropdown.querySelector('[data-testid="block-info"]')),
              control: rect(dropdown.querySelector('.container > .wrap')),
            },
            segmented: {
              root: rect(segmented),
              label: rect(segmented.querySelector('[data-testid="block-info"]')),
              control: rect(
                segmented.querySelector(':scope > .wrap:not([data-testid="status-tracker"])')
              ),
            },
          };
        }"""
    )
    for key in ("root", "label", "control"):
        left = geometry["dropdown"][key]
        right = geometry["segmented"][key]
        assert left["top"] == pytest.approx(right["top"], abs=1), geometry
        assert left["bottom"] == pytest.approx(right["bottom"], abs=1), geometry
        assert left["height"] == pytest.approx(right["height"], abs=1), geometry
        if key != "label":
            assert left["width"] == pytest.approx(right["width"], abs=1), geometry


def test_runtime_default_fields_share_one_vertical_grid(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.get_by_role("tab", name="常规设置").click()

    geometry = page.evaluate(
        """() => {
          const measure = (selector) => {
            const root = document.querySelector(selector);
            const info = root.querySelector('.info-text');
            const input = root.querySelector('textarea, input');
            const rootRect = root.getBoundingClientRect();
            const infoRect = info.getBoundingClientRect();
            const inputRect = input.getBoundingClientRect();
            return {
              rootTop: rootRect.top,
              rootBottom: rootRect.bottom,
              infoTop: infoRect.top,
              infoBottom: infoRect.bottom,
              inputTop: inputRect.top,
              inputBottom: inputRect.bottom,
              inputHeight: inputRect.height,
            };
          };
          return {
            output: measure('#runtime-output-dir'),
            config: measure('#runtime-config-path'),
          };
        }"""
    )
    for key in geometry["output"]:
        assert geometry["output"][key] == pytest.approx(geometry["config"][key], abs=1)


def test_sidebar_uses_paperbanana_cn_branding(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)
    sidebar = page.locator("#studio-nav")
    logo = sidebar.locator("#studio-brand img.brand-mark")
    playwright.expect(logo).to_be_visible()
    assert logo.get_attribute("src") == "./paperbanana-assets/paperbanana-cn-logo.jpg"
    assert logo.evaluate("(image) => image.complete && image.naturalWidth === 940")
    playwright.expect(sidebar.get_by_text("PaperBanana-CN", exact=True)).to_be_visible()
    playwright.expect(sidebar.get_by_text("开发者 mituan", exact=True)).to_be_visible()
    link_box = sidebar.get_by_role("link", name="github.com/mituan-ai").bounding_box()
    credit_box = sidebar.get_by_text("开发者 mituan", exact=True).bounding_box()
    settings_box = page.locator("#nav-settings").bounding_box()
    assert link_box and credit_box and settings_box
    assert abs(link_box["x"] - credit_box["x"]) <= 1
    assert abs(link_box["x"] - (settings_box["x"] + 11)) <= 1
    text = sidebar.inner_text()
    assert "PB" not in text
    assert "llmsresearch/paperbanana" not in text
    assert "非官方社区实现" not in text


def test_plot_is_vlm_only_and_ignores_missing_image_connection(
    running_studio: RunningStudio, browser_page, tmp_path: Path
):
    running_studio.manager.delete_profile("test-image")
    data = tmp_path / "plot.csv"
    data.write_text("x,y\n1,2\n", encoding="utf-8")

    page = browser_page
    _open_studio(page, running_studio.url)
    playwright.expect(page.locator("#diagram-generate")).to_be_disabled()
    playwright.expect(page.locator("#diagram-connection-gate").last).to_be_visible()
    page.locator("#diagram-open-settings").click()
    page.locator("#page-settings").wait_for(state="visible")

    page.locator("#nav-evaluate").click()
    page.locator("#page-evaluate").wait_for(state="visible")
    playwright.expect(page.locator("#evaluate-run")).to_be_enabled()
    page.locator("#nav-orchestrate").click()
    page.locator("#page-orchestrate").wait_for(state="visible")
    playwright.expect(page.locator("#orchestrate-run")).to_be_disabled()
    page.locator("#nav-batch").click()
    page.locator("#page-batch").wait_for(state="visible")
    playwright.expect(page.locator("#batch-run")).to_be_disabled()
    page.locator("#batch-type").get_by_label("统计图", exact=True).check()
    playwright.expect(page.locator("#batch-run")).to_be_enabled()

    page.locator("#nav-plot").click()
    page.locator("#page-plot").wait_for(state="visible")
    page.locator("#plot-data-file input[type=file]").set_input_files(str(data))
    _control(page, "plot-intent").fill("Compare x and y")
    page.locator("#plot-generate").click()
    playwright.expect(page.locator("#plot-generate")).to_be_enabled()

    assert len(running_studio.probe.plot_calls) == 1
    settings = running_studio.probe.plot_calls[0]["settings"]
    assert settings.effective_vlm_model == "vlm-test-model"
    assert settings.image_provider == "none"
    assert settings.image_api_key is None


def test_forced_dark_preferences_still_render_high_contrast_light_theme(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    page.emulate_media(color_scheme="dark")
    page.goto(f"{running_studio.url}/?__theme=dark", wait_until="domcontentloaded")
    page.locator("#studio-workflows").wait_for(state="visible")
    colors = page.evaluate(
        """() => {
          const input = document.querySelector('#diagram-context textarea');
          const shell = document.querySelector('#studio-shell');
          return {
            shellBackground: getComputedStyle(shell).backgroundColor,
            inputBackground: getComputedStyle(input).backgroundColor,
            inputColor: getComputedStyle(input).color,
            colorScheme: getComputedStyle(document.documentElement).colorScheme,
          };
        }"""
    )
    assert colors["shellBackground"] == "rgb(238, 241, 240)"
    assert colors["inputBackground"] == "rgb(255, 255, 255)"
    assert colors["inputColor"] == "rgb(24, 33, 30)"
    assert colors["colorScheme"] == "light"


def test_visible_desktop_text_has_readable_contrast_and_type_scale(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    contrast_audit = """(selectors) => {
          const parse = (value) => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
          const luminance = ([r, g, b]) => {
            const channels = [r, g, b].map((v) => {
              v /= 255;
              return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
            });
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
          };
          const background = (element) => {
            let current = element;
            while (current) {
              const color = getComputedStyle(current).backgroundColor;
              if (color && !color.endsWith(', 0)') && color !== 'transparent') return color;
              current = current.parentElement;
            }
            return 'rgb(255, 255, 255)';
          };
          return selectors.flatMap((selector) => {
            const element = document.querySelector(selector);
            if (!element || !element.checkVisibility()) return [];
            const style = getComputedStyle(element);
            const foreground = luminance(parse(style.color));
            const backdrop = luminance(parse(background(element)));
            const contrast = (Math.max(foreground, backdrop) + 0.05) /
              (Math.min(foreground, backdrop) + 0.05);
            return [{
              selector,
              contrast,
              fontSize: Number.parseFloat(style.fontSize),
              opacity: Number.parseFloat(style.opacity),
            }];
          });
        }"""
    samples = page.evaluate(
        contrast_audit,
        [
            "#studio-brand .brand-name",
            "#studio-brand .brand-edition",
            "#studio-nav .nav-group-label .prose",
            "#studio-nav .nav-item",
            "#studio-nav .nav-item.primary",
            "#sidebar-disclaimer .developer-credit",
            "#current-page-title h1",
            '#diagram-context [data-testid="block-info"]',
            "#diagram-context textarea",
            "#diagram-generate",
        ],
    )
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.get_by_role("tab", name="常规设置").click()
    samples.extend(
        page.evaluate(
            contrast_audit,
            [
                '#page-settings [role="tab"][aria-selected="true"]',
                "#studio-locale-switch label:has(input:checked)",
            ],
        )
    )
    assert len(samples) >= 11
    for sample in samples:
        assert sample["contrast"] >= 4.5, sample
        assert sample["opacity"] >= 0.9, sample
    sizes = {sample["selector"]: sample["fontSize"] for sample in samples}
    assert sizes["#studio-nav .nav-item"] >= 14
    assert sizes["#studio-nav .nav-group-label .prose"] >= 12
    assert sizes["#diagram-context textarea"] >= 15


def test_all_workflow_neutral_text_is_high_contrast(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)
    audit = """() => {
      const rgb = (value) => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
      const luminance = (value) => {
        const channels = rgb(value).map((channel) => {
          channel /= 255;
          return channel <= 0.04045
            ? channel / 12.92
            : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
      };
      const background = (element) => {
        let current = element;
        while (current) {
          const value = getComputedStyle(current).backgroundColor;
          const values = value.match(/[\\d.]+/g)?.map(Number) ?? [];
          if (values.length === 3 || (values.length === 4 && values[3] >= 0.98)) return value;
          current = current.parentElement;
        }
        return 'rgb(255, 255, 255)';
      };
      const directText = (element) => [...element.childNodes]
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent.trim()).filter(Boolean).join(' ');
      return [...document.querySelectorAll('#studio-shell *')].flatMap((element) => {
        const text = directText(element);
        if (!text || !element.checkVisibility()) return [];
        const style = getComputedStyle(element);
        const channels = rgb(style.color);
        const neutral = Math.max(...channels) - Math.min(...channels) <= 24;
        const nearWhite = Math.min(...channels) >= 235;
        let opacity = 1;
        for (let current = element; current; current = current.parentElement) {
          opacity *= Number.parseFloat(getComputedStyle(current).opacity || '1');
        }
        const foreground = luminance(style.color);
        const backdrop = luminance(background(element));
        return [{
          text: text.slice(0, 80),
          color: style.color,
          contrast: (Math.max(foreground, backdrop) + 0.05) /
            (Math.min(foreground, backdrop) + 0.05),
          opacity,
          neutral: neutral && !nearWhite,
        }];
      });
    }"""
    failures = []
    for page_id in [item.key for item in WORKFLOW_SPECS]:
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")
        for sample in page.evaluate(audit):
            if sample["neutral"] and sample["contrast"] < 7:
                failures.append({"page": page_id, **sample})
    assert failures == []


def test_desktop_layout_contract_at_supported_viewports(
    running_studio: RunningStudio, browser_page, tmp_path: Path
):
    page = browser_page
    _open_studio(page, running_studio.url)
    viewports = [
        (1200, 800),
        (1279, 800),
        (1280, 800),
        (1440, 900),
        (1599, 900),
        (1600, 900),
        (1920, 1080),
        (1921, 1080),
        (2048, 1080),
        (2560, 1440),
    ]
    for width, height in viewports:
        page.set_viewport_size({"width": width, "height": height})

        dimensions = page.evaluate(
            "() => ({ width: document.documentElement.scrollWidth, "
            "height: document.documentElement.scrollHeight })"
        )
        assert dimensions["width"] == width
        assert dimensions["height"] == height

        shell = page.locator("#studio-shell").bounding_box()
        navigation = page.locator("#studio-nav").bounding_box()
        main = page.locator("#studio-main").bounding_box()
        header = page.locator("#studio-header").bounding_box()
        title = page.locator("#current-page-title").bounding_box()
        content = page.locator("#studio-content").bounding_box()
        workbench = page.locator("#diagram-workbench").bounding_box()
        input_panel = page.locator("#diagram-input-panel").bounding_box()
        result_panel = page.locator("#diagram-result-panel").bounding_box()
        generate = page.locator("#diagram-generate").bounding_box()
        context = page.locator("#diagram-context").last.bounding_box()
        context_file = page.locator("#diagram-context-file").last.bounding_box()
        assert shell and navigation and main and header and title and content
        assert workbench and input_panel and result_panel and generate
        assert context and context_file

        expected_nav_width = 224
        expected_input_width = 440
        input_padding = page.locator("#diagram-input-panel").evaluate(
            "(element) => parseFloat(getComputedStyle(element).paddingLeft)"
        )

        assert shell["x"] == pytest.approx(0, abs=1)
        assert shell["width"] == pytest.approx(width, abs=1)
        assert navigation["x"] == pytest.approx(0, abs=1)
        assert navigation["width"] == pytest.approx(expected_nav_width, abs=1)
        assert main["x"] == pytest.approx(navigation["width"], abs=1)
        assert main["x"] + main["width"] == pytest.approx(width, abs=1)
        assert header["x"] == pytest.approx(main["x"], abs=1)
        assert header["x"] + header["width"] == pytest.approx(width, abs=1)
        assert content["x"] == pytest.approx(main["x"], abs=1)
        assert content["x"] + content["width"] == pytest.approx(width, abs=1)
        assert workbench["x"] == pytest.approx(main["x"], abs=1)
        assert workbench["y"] == pytest.approx(header["y"] + header["height"], abs=1)
        assert workbench["x"] + workbench["width"] == pytest.approx(width, abs=1)
        assert workbench["y"] + workbench["height"] == pytest.approx(height, abs=1)
        assert input_panel["width"] == pytest.approx(expected_input_width, abs=1)
        assert input_panel["x"] + input_panel["width"] == pytest.approx(result_panel["x"], abs=1)
        assert result_panel["x"] + result_panel["width"] == pytest.approx(width, abs=1)
        assert result_panel["width"] >= 400
        assert title["x"] == pytest.approx(input_panel["x"] + input_padding, abs=1)
        assert generate["y"] + generate["height"] <= height - 12
        assert context["height"] >= 180
        assert context_file["height"] >= 128
        assert context["y"] + context["height"] <= context_file["y"] + 1

        screenshot = page.screenshot(path=str(tmp_path / f"studio-{width}x{height}.png"))
        image = Image.open(BytesIO(screenshot)).convert("RGB").resize((32, 32))
        assert len(set(image.getdata())) > 20


def test_browser_tab_uses_product_title(running_studio: RunningStudio, browser_page):
    _open_studio(browser_page, running_studio.url)

    assert browser_page.title() == "PaperBanana-CN"


def test_status_and_command_colors_follow_one_semantic_system(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)

    status = page.locator("#diagram-status")
    status_inner = status.locator(".run-status")
    assert status.evaluate("(node) => getComputedStyle(node).borderWidth") == "0px"
    assert status.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(232, 243, 239)"
    )
    assert status_inner.evaluate("(node) => getComputedStyle(node).borderWidth") == "0px"
    assert status_inner.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgba(0, 0, 0, 0)"
    )

    primary = page.locator("#diagram-generate")
    assert primary.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(20, 120, 98)"
    )

    page.locator("#nav-continue").click()
    page.locator("#page-continue").wait_for(state="visible")
    disabled = page.locator("#continue-run")
    playwright.expect(disabled).to_be_disabled()
    assert disabled.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(227, 232, 229)"
    )

    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    secondary = page.locator("#connection-vlm-save")
    save_and_use = page.locator("#connection-vlm-save-use")
    assert secondary.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(255, 255, 255)"
    )
    assert save_and_use.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(20, 120, 98)"
    )

    page.get_by_role("tab", name="图像生成连接").click()
    paid = page.locator("#connection-image-test")
    danger = page.locator("#connection-image-delete")
    assert paid.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(255, 247, 230)"
    )
    assert danger.evaluate("(node) => getComputedStyle(node).backgroundColor") == (
        "rgb(255, 248, 248)"
    )


def test_workflow_controls_are_not_clipped_and_scroll_is_single_axis(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    audit = """() => {
      const clipped = [...document.querySelectorAll(
        '.workflow-input-panel .block, .workflow-input-panel .form'
      )].flatMap((element) => {
        if (!element.checkVisibility()) return [];
        const verticalClip = element.scrollHeight - element.clientHeight;
        const horizontalClip = element.scrollWidth - element.clientWidth;
        if (verticalClip <= 2 && horizontalClip <= 2) return [];
        return [{
          id: element.id,
          text: (element.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80),
          verticalClip,
          horizontalClip,
        }];
      });
      const resultPanels = [...document.querySelectorAll('.workflow-result-panel')]
        .filter((element) => element.checkVisibility())
        .map((element) => ({
          id: element.id,
          overflowX: getComputedStyle(element).overflowX,
          overflowY: getComputedStyle(element).overflowY,
        }));
      const inputPanels = [...document.querySelectorAll('.workflow-input-panel')]
        .filter((element) => element.checkVisibility())
        .map((element) => ({
          id: element.id,
          overflowX: getComputedStyle(element).overflowX,
        }));
      return {clipped, resultPanels, inputPanels};
    }"""
    failures = []
    for page_id in [item.key for item in WORKFLOW_SPECS if item.key not in {"runs", "settings"}]:
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")
        result = page.evaluate(audit)
        if result["clipped"]:
            failures.append({"page": page_id, "clipped": result["clipped"]})
        assert all(item["overflowX"] == "hidden" for item in result["inputPanels"])
        assert all(
            item["overflowX"] == "hidden" and item["overflowY"] == "hidden"
            for item in result["resultPanels"]
        )
    assert failures == []


def test_visible_scroll_containers_are_intentional(running_studio: RunningStudio, browser_page):
    """Reject Gradio's decorative scrollbars on blocks that do not own scrolling."""
    page = browser_page
    _open_studio(page, running_studio.url)
    audit = """() => [...document.querySelectorAll('#studio-shell *')].flatMap((element) => {
      if (!element.checkVisibility()) return [];
      const style = getComputedStyle(element);
      const scrollX = ['auto', 'scroll'].includes(style.overflowX);
      const scrollY = ['auto', 'scroll'].includes(style.overflowY);
      if (!scrollX && !scrollY) return [];
      const allowed = element.matches([
        '.workflow-input-panel',
        '.workflow-input-scroll',
        '.connection-detail',
        '#page-runs',
        '.evaluation-result',
        'textarea',
      ].join(','));
      return [{
        allowed,
        tag: element.tagName,
        id: element.id,
        classes: [...element.classList].filter((name) => !name.startsWith('svelte-')),
        text: (element.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80),
        overflowX: style.overflowX,
        overflowY: style.overflowY,
        clipX: element.scrollWidth - element.clientWidth,
        clipY: element.scrollHeight - element.clientHeight,
      }];
    })"""
    failures = []
    for page_id in [item.key for item in WORKFLOW_SPECS]:
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")
        for sample in page.evaluate(audit):
            if not sample["allowed"]:
                failures.append({"page": page_id, **sample})
            elif sample["overflowX"] in {"auto", "scroll"} and sample["clipX"] > 2:
                failures.append({"page": page_id, "reason": "horizontal scroll", **sample})
    assert failures == []


def test_settings_single_line_controls_share_one_height(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")

    def input_height(elem_id: str) -> float:
        component = page.locator(f"#{elem_id}")
        dropdown = component.locator(".container > .wrap")
        control = dropdown.first if dropdown.count() else component.locator("input, textarea").first
        box = control.bounding_box()
        assert box is not None
        return box["height"]

    for role in ("vlm", "image"):
        page.get_by_role(
            "tab", name="视觉语言模型连接" if role == "vlm" else "图像生成连接"
        ).click()
        ids = [
            f"connection-{role}-name",
            f"connection-{role}-provider",
            f"connection-{role}-timeout",
            f"connection-{role}-url",
            f"connection-{role}-model",
            f"connection-{role}-api-key",
        ]
        if role == "image":
            ids.append("connection-image-size-mode")
        heights = {elem_id: input_height(elem_id) for elem_id in ids}
        assert min(heights.values()) >= 40, heights
        assert max(heights.values()) - min(heights.values()) <= 2, heights


def test_settings_connection_actions_are_reachable_at_minimum_viewport(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 800})
    _open_studio(page, running_studio.url)
    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page_box = page.locator("#page-settings").bounding_box()
    assert page_box is not None

    for role, tab_name in (("vlm", "视觉语言模型连接"), ("image", "图像生成连接")):
        page.get_by_role("tab", name=tab_name).click()
        detail = page.locator(".connection-detail:visible")
        detail_box = detail.bounding_box()
        assert detail_box is not None
        for action in ("save", "save-use", "test", "clear", "delete"):
            button = page.locator(f"#connection-{role}-{action}")
            playwright.expect(button).to_be_visible()
            playwright.expect(button).to_be_in_viewport(ratio=1)
            box = button.bounding_box()
            assert box is not None
            assert detail_box["y"] <= box["y"]
            assert box["y"] + box["height"] <= detail_box["y"] + detail_box["height"] + 1
            assert box["y"] + box["height"] <= page_box["y"] + page_box["height"]


def test_generation_controls_form_one_aligned_row_at_minimum_viewport(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 800})
    _open_studio(page, running_studio.url)
    controls = [
        page.locator(f"#diagram-{name}")
        for name in ("output-format", "resolution", "refinement-iterations")
    ]
    controls[0].scroll_into_view_if_needed()
    boxes = [control.bounding_box() for control in controls]
    assert all(boxes)
    assert max(box["y"] for box in boxes) - min(box["y"] for box in boxes) <= 2
    assert max(box["height"] for box in boxes) - min(box["height"] for box in boxes) <= 2
    assert max(box["width"] for box in boxes) - min(box["width"] for box in boxes) <= 3
    assert max(box["height"] for box in boxes) <= 96


def test_result_surfaces_have_deliberate_empty_states(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)
    expected = {
        "diagram": ("#diagram-result-stage", "生成完成后将在这里显示"),
        "plot": ("#plot-result-stage", "生成完成后将在这里显示"),
        "continue": ("#continue-result-stage", "选择历史任务后将在这里显示"),
        "composite": ("#composite-result-stage", "组合完成后将在这里显示"),
        "runs": ("#runs-selected-image-stage", "选择历史任务后将在这里显示"),
    }
    for page_id, (selector, message) in expected.items():
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")
        playwright.expect(page.locator(selector)).to_contain_text(message)


def test_upload_surfaces_are_visibly_framed(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)
    surfaces = [
        ("diagram", "#diagram-context-file"),
        ("evaluate", "#evaluate-generated-image"),
        ("evaluate", "#evaluate-reference-image"),
    ]

    for page_id, selector in surfaces:
        page.locator(f"#nav-{page_id}").click()
        page.locator(f"#page-{page_id}").wait_for(state="visible")
        page.locator(selector).scroll_into_view_if_needed()
        appearance = page.locator(selector).evaluate(
            """element => {
              const style = getComputedStyle(element);
              const label = element.querySelector('[data-testid="block-label"]');
              const labelStyle = getComputedStyle(label);
              return {
                background: style.backgroundColor,
                borderWidth: style.borderTopWidth,
                borderStyle: style.borderTopStyle,
                borderColor: style.borderTopColor,
                radius: style.borderRadius,
                labelBackground: labelStyle.backgroundColor,
              };
            }"""
        )
        assert appearance["background"] != "rgba(0, 0, 0, 0)", appearance
        assert appearance["borderWidth"] == "1px", appearance
        assert appearance["borderStyle"] == "solid", appearance
        assert appearance["borderColor"] != "rgba(0, 0, 0, 0)", appearance
        assert appearance["radius"] in {"6px", "7px"}, appearance
        assert appearance["labelBackground"] == "rgb(255, 255, 255)", appearance


def test_settings_content_and_runs_workspace_do_not_create_long_documents(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 800})
    _open_studio(page, running_studio.url)

    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.get_by_role("tab", name="图像生成连接").click()
    settings_geometry = page.evaluate(
        """() => {
          const pageRoot = document.querySelector('#page-settings');
          const editor = [...document.querySelectorAll('.connection-master-detail')]
            .find((element) => element.checkVisibility());
          const pageRect = pageRoot.getBoundingClientRect();
          const editorRect = editor.getBoundingClientRect();
          return {
            pageClip: pageRoot.scrollHeight - pageRoot.clientHeight,
            editorBottom: editorRect.bottom,
            pageBottom: pageRect.bottom,
          };
        }"""
    )
    assert settings_geometry["pageClip"] <= 2
    assert settings_geometry["editorBottom"] <= settings_geometry["pageBottom"] + 1

    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator("#nav-runs").click()
    page.locator("#page-runs").wait_for(state="visible")
    runs_geometry = page.evaluate(
        """() => {
          const root = document.querySelector('#page-runs');
          return {
            clip: root.scrollHeight - root.clientHeight,
            overflowY: getComputedStyle(root).overflowY,
          };
        }"""
    )
    assert runs_geometry["clip"] <= 2
    assert runs_geometry["overflowY"] == "hidden"


def test_all_pages_have_no_horizontal_or_empty_textarea_overflow(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 800})
    _open_studio(page, running_studio.url)
    failures = []
    for page_id in [item.key for item in WORKFLOW_SPECS]:
        page.locator(f"#nav-{page_id}").click()
        active_page = page.locator(f"#page-{page_id}")
        active_page.wait_for(state="visible")
        result = page.evaluate(
            """(pageId) => {
              const describe = (element) => ({
                id: element.id,
                classes: [...element.classList].filter((name) => !name.startsWith('svelte-')),
                clipX: element.scrollWidth - element.clientWidth,
                clipY: element.scrollHeight - element.clientHeight,
              });
              const pageRoot = document.querySelector(`#page-${pageId}`);
              const roots = [
                document.querySelector('#studio-nav'),
                pageRoot,
                ...document.querySelectorAll(`#page-${pageId} .workflow-input-panel`),
                ...document.querySelectorAll(`#page-${pageId} .workflow-result-panel`),
              ].filter(Boolean);
              const horizontal = roots.flatMap((element) => {
                const item = describe(element);
                const overflowX = getComputedStyle(element).overflowX;
                return item.clipX > 2 && ['auto', 'scroll'].includes(overflowX)
                  ? [{...item, overflowX}]
                  : [];
              });
              const outOfViewport = [...pageRoot.querySelectorAll('*')]
                .filter((element) => element.checkVisibility())
                .flatMap((element) => {
                  const rect = element.getBoundingClientRect();
                  return rect.left < -1 || rect.right > innerWidth + 1
                    ? [{
                        ...describe(element),
                        left: rect.left,
                        right: rect.right,
                        viewportWidth: innerWidth,
                      }]
                    : [];
                });
              const emptyTextareas = [...document.querySelectorAll(
                `#page-${pageId} textarea`
              )].filter((element) => element.checkVisibility() && !element.value)
                .map(describe).filter((item) => item.clipY > 2 || item.clipX > 2);
              return {horizontal, outOfViewport, emptyTextareas};
            }""",
            page_id,
        )
        if result["horizontal"] or result["outOfViewport"] or result["emptyTextareas"]:
            failures.append({"page": page_id, **result})
    assert failures == []


def test_primary_actions_have_a_separate_non_overlapping_action_row(
    running_studio: RunningStudio, browser_page
):
    page = browser_page
    _open_studio(page, running_studio.url)
    workflow_ids = [
        "diagram",
        "plot",
        "continue",
        "evaluate",
        "orchestrate",
        "batch",
        "sweep",
        "composite",
    ]
    failures = []
    for page_id in workflow_ids:
        page.locator(f"#nav-{page_id}").click()
        active_page = page.locator(f"#page-{page_id}")
        active_page.wait_for(state="visible")
        result = active_page.evaluate(
            """root => {
              const panel = root.querySelector('.workflow-input-panel');
              const scroll = panel?.querySelector(':scope > .workflow-input-scroll');
              const action = panel?.querySelector(':scope > .primary-action');
              if (!panel || !scroll || !action) return {structure: false};
              const scrollRect = scroll.getBoundingClientRect();
              const actionRect = action.getBoundingClientRect();
              return {
                structure: true,
                overlap: Math.max(0, scrollRect.bottom - actionRect.top),
                actionBottomGap: panel.getBoundingClientRect().bottom - actionRect.bottom,
                actionVisible: action.checkVisibility(),
              };
            }"""
        )
        if (
            not result.get("structure")
            or not result.get("actionVisible")
            or result.get("overlap", 1) > 0
            or result.get("actionBottomGap", 99) > 20
        ):
            failures.append({"page": page_id, **result})
    assert failures == []


def test_secondary_pages_keep_compact_form_geometry(running_studio: RunningStudio, browser_page):
    page = browser_page
    _open_studio(page, running_studio.url)

    page.locator("#nav-runs").click()
    page.locator("#page-runs").wait_for(state="visible")
    for elem_id in ("runs-run-selector", "runs-batch-selector"):
        box = page.locator(f"#{elem_id}").bounding_box()
        assert box is not None
        assert box["height"] <= 95

    page.locator("#nav-settings").click()
    page.locator("#page-settings").wait_for(state="visible")
    page.get_by_role("tab", name="常规设置").click()
    for elem_id in ("runtime-output-dir", "runtime-config-path"):
        control = page.locator(f"#{elem_id}").locator("textarea, input").first
        box = control.bounding_box()
        assert box is not None and 40 <= box["height"] <= 46
        assert control.evaluate("element => getComputedStyle(element).borderTopWidth") == "1px"
