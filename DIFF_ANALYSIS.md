# PaperBanana-CN 差异记录

## 目标

- 以 `PaperBanana-Pro/main@10a73b0` 为基线，尽量贴回官方逻辑。
- 只保留一条核心差异：VLM 与图像链路可分别填写 `URL / API / MODEL`。
- `gpt-image-2-vip(apiyi)` 只保留后端小兼容，不进入主配置模型。

## 已完成

- `demo.py`
  - 主路径不再做 APIYI URL 强制、自动落盘或额外 session-state 同步。
  - 双链路仍保留为两个独立连接块，保存只走显式按钮。
- `utils/config_loader.py`
  - 恢复为官方配置优先级：环境变量 -> `configs/local/*.txt` -> `configs/model_config.yaml`。
  - 不再依赖 `provider_settings.yaml`。
- `utils/runtime_settings.py` / `utils/provider_connections.py`
  - 保留文本链路与图像链路分离能力。
  - builtin provider 仍按官方来源取值；双链路长期保存走自定义连接。
- `utils/image_generation_options.py` / `utils/generation_utils.py`
  - 图像尺寸归一化收敛到单一路径。
  - APIYI 只在图像 URL 明确是 APIYI，或 VIP 模型且图像 URL 留空时启用；不覆盖已填写的图像 URL。

## 仍保留

- `image_*` 字段：用于双链路运行时分离。
- `gpt-image-2-vip(apiyi)`：仅作兼容入口。
- 其它非核心差异先不碰，按真实报错再收敛。

## 验证

- `uv run python -m py_compile demo.py cli.py main.py`
- `uv run pytest -q`
- `uv run paperbanana --help`
- `timeout 20s uv run paperbanana gui --server.headless true --server.port 8521`
