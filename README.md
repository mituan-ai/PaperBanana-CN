<p align="center">
  <img src="assets/hero_banner.png" alt="PaperBanana-CN" width="420">
</p>

<h1 align="center">PaperBanana-CN · 纸香蕉</h1>

<p align="center">
  <strong>科研绘图，中英文友好，模型随心接入</strong><br>
  GPT-5.5 · GPT-Image-2 · Gemini · 主流中转站兼容 · 中文工作流优先
</p>

<p align="center">
  <a href="https://github.com/917940234/PaperBanana-CN/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="License"></a>&nbsp;
  <img src="https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white" alt="Python">&nbsp;
  <a href="https://github.com/917940234/PaperBanana-CN/actions"><img src="https://img.shields.io/github/actions/workflow/status/917940234/PaperBanana-CN/ci.yml?label=CI&logo=github" alt="CI"></a>&nbsp;
  <img src="https://img.shields.io/badge/GPT--5.5-ready-111827" alt="GPT-5.5 ready">&nbsp;
  <img src="https://img.shields.io/badge/GPT--Image--2-ready-7C3AED" alt="GPT-Image-2 ready">&nbsp;
  <img src="https://img.shields.io/badge/Gemini-gateway%20ready-4285F4" alt="Gemini gateway ready">
  <br>
  <a href="https://huggingface.co/datasets/dwzhu/PaperBananaBench"><img src="https://img.shields.io/badge/🤗_Dataset-PaperBananaBench-yellow" alt="Dataset"></a>&nbsp;
  <a href="https://huggingface.co/papers/2601.23265"><img src="https://img.shields.io/badge/📄_Paper-HuggingFace-orange" alt="Paper"></a>&nbsp;
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome">
</p>

---

## 这是什么？

**PaperBanana-CN** 是面向中文与英文科研写作场景的学术绘图工作台。它继承 PaperBanana 的多 Agent 学术图解生成思路，同时重做了本地 GUI、后台任务、批量导出、历史回放和模型接入体验。

本仓库最核心的目标很直接：

> 让 PaperBanana 更适合中文科研用户，也更适合今天常见的 GPT / Gemini / 中转站平台使用方式。

你可以把 **VLM 文本规划** 和 **文生图生成** 分成两条独立链路：文本可以走 GPT-5.5，图像可以走 GPT-Image-2；也可以文本走 Gemini、图像走 Gemini；还可以混合使用不同中转站的 Base URL、API Key 和模型名。

---

## 核心亮点

| 能力 | 说明 |
| --- | --- |
| **中英文科研绘图友好** | 中文界面、中文提示词输入、英文论文内容也能直接处理，适合国内科研工作流。 |
| **GPT-5.5 / GPT-Image-2 适配** | 内置 GPT 文本模型与 OpenAI 图像模型配置入口，支持 OpenAI-compatible 中转站。 |
| **Gemini 图文链路适配** | 支持 Gemini VLM 与 Gemini 图像模型，兼容 Gemini-compatible 网关地址。 |
| **VLM 与文生图彻底解耦** | 两块设置：`VLM 文本` 和 `文生图`。每块都可单独选择 GPT 或 Gemini。 |
| **分辨率与比例真实传参** | Gemini 使用 `image_config`，GPT-Image-2 自动把 UI 中的分辨率/宽高比转换为 OpenAI `size`。 |
| **主流中转站平台友好** | 每条链路独立填写 API Key、Base URL、模型名，适配常见聚合平台、反代平台和自建 gateway。 |
| **多候选后台生成** | Streamlit 前端不阻塞，支持并发生成、实时事件流、候选收藏/淘汰/最终选择。 |
| **全流程导出与回放** | Bundle/ZIP 保存候选图、阶段描述、评审建议、绘图代码和原始 JSON。 |
| **Plot 与 Diagram 双模式** | 支持论文示意图生成，也支持统计图表代码生成与本地重渲染。 |

---

## 模型与中转站配置

PaperBanana-CN 把模型调用拆成两类：

1. **VLM 文本**：用于规划、检索判断、图解描述、评审建议。
2. **文生图**：用于真正生成 diagram 图像。

每一类都可以选择 GPT 或 Gemini，并分别配置：

- API Key
- Base URL
- 模型名称

推荐使用环境变量或 `configs/local/*.txt` 保存密钥，不要把真实 key 写进 Git。

| 链路 | GPT / OpenAI-compatible | Gemini-compatible |
| --- | --- | --- |
| VLM API Key | `PAPERBANANA_OPENAI_VLM_API_KEY` | `PAPERBANANA_GEMINI_VLM_API_KEY` |
| 文生图 API Key | `PAPERBANANA_OPENAI_IMAGE_API_KEY` | `PAPERBANANA_GEMINI_IMAGE_API_KEY` |
| Base URL | `PAPERBANANA_OPENAI_BASE_URL`，通常形如 `https://xxx/v1` | `PAPERBANANA_GEMINI_BASE_URL`，通常形如 `https://xxx` |
| VLM 模型 | `PAPERBANANA_OPENAI_VLM_MODEL`，例如 `gpt-5.5` | `PAPERBANANA_GEMINI_VLM_MODEL` |
| 文生图模型 | `PAPERBANANA_OPENAI_IMAGE_MODEL`，例如 `gpt-image-2` | `PAPERBANANA_GEMINI_IMAGE_MODEL` |

> OpenAI-compatible SDK 会在 `base_url` 后追加 `/images/generations`，因此 OpenAI 中转站一般要填写带 `/v1` 的 Base URL，例如 `https://api.example.com/v1`。

### 分辨率、比例与精修边界

生成候选方案时，GUI 的“宽高比”和“图像分辨率”会按当前 **文生图 Provider** 转成真实 API 参数：

| 文生图 Provider | 参数策略 | 示例 |
| --- | --- | --- |
| GPT / OpenAI-compatible | 转成 OpenAI Images `size` | `16:9 + 4K → 3840x2160`，`9:16 + 4K → 2160x3840`，`1:1 + 2K → 2048x2048` |
| Gemini-compatible | 写入 Gemini `image_config.aspect_ratio` 与 `image_config.image_size` | `16:9 + 4K → aspect_ratio=16:9, image_size=4K` |
| OpenRouter / Evolink | 透传为对应 provider 的图像配置字段 | `aspect_ratio`、`image_size` 或 `quality` |

当前能力边界请特别注意：

- **GPT / OpenAI-compatible 文生图生成**：已支持，用于生成候选方案，包含 GPT-Image-2 尺寸转换。
- **Gemini 图像精修**：已支持，上传图像后走 Gemini 图像模型并传入比例/分辨率配置。
- **Evolink 图像精修**：保留支持路径。
- **OpenAI image edit / GPT 图像精修**：当前尚未接入 `images.edits`，因此精修页选择 GPT 图像链路时会被前端拦截；这不是 API Key 或模型名配置错误，而是尚未实现的能力边界。

---

## 快速开始

```bash
git clone https://github.com/917940234/PaperBanana-CN.git
cd PaperBanana-CN
uv python install 3.12
uv sync --locked
uv tool install --editable . --force
```

未来发布到 PyPI 后，也会支持：`uv tool install paperbanana-cn`。

启动 GUI：

```bash
paperbanana gui
```

或者直接：

```bash
paperbanana
```

如果只想本地运行而不安装命令：

```bash
uv run streamlit run demo.py
```

---

## 典型使用方式

### 1. 生成学术图解

输入论文方法段落、图注或可视化意图，选择候选数，启动后台任务。系统会自动完成：

```text
检索参考 → 规划图解 → 首轮出图 → 评审 → 修正出图 → 导出结果
```

适合生成方法框架图、流程图、机制图、系统图和论文级 graphical abstract 草图。

### 2. 生成统计图表

选择 `plot` 任务后，系统会更偏向生成 Matplotlib 代码，并在本地执行渲染。适合把实验数据、CSV、表格或绘图意图转成论文图。

### 3. 图像精修

在精修工作台中上传已有候选图或外部图片，输入修改要求，生成多个精修版本，并保留版本链。

---

## GUI 工作台

| 工作区 | 作用 |
| --- | --- |
| **生成候选方案** | 多候选并发生成，实时展示状态、事件、候选图和阶段描述。 |
| **候选决策工作台** | 收藏、淘汰、设为最终候选，并按筛选范围批量导出。 |
| **历史运行回放** | 读取历史 bundle，恢复完整运行过程和结果。 |
| **精修图像** | 多版本图像重绘，支持从任意历史版本继续修改。 |

---

## CLI 与 Viewer

批处理运行：

```bash
paperbanana run --task_name diagram --exp_mode demo_planner_critic --provider gemini
```

查看流程演化：

```bash
paperbanana viewer evolution
```

查看参考评测：

```bash
paperbanana viewer eval
```

可用命令：

```bash
paperbanana-cn --help
```

---

## 数据集

推荐下载 [`dwzhu/PaperBananaBench`](https://huggingface.co/datasets/dwzhu/PaperBananaBench) 并放到：

```text
data/PaperBananaBench/
```

它用于 few-shot 检索、参考样例和基准评测。若只想快速试用，可以在 GUI 中把检索设置为 `none`。

---

## 项目结构

```text
PaperBanana-CN/
├── agents/          # 多 Agent 阶段实现
├── configs/         # 模型、中转站与本地密钥配置
├── prompts/         # 任务提示词
├── providers/       # Provider 接入层
├── utils/           # 运行时、配置、导出、图像处理工具
├── visualize/       # Streamlit Viewer
├── demo.py          # 主 GUI
├── main.py          # 批处理 CLI
├── cli.py           # paperbanana 命令入口
└── pyproject.toml   # Python 项目元数据
```

---

## 与原项目的关系

PaperBanana-CN 不是从零开始的新方法，而是建立在 PaperBanana 生态上的中文增强与网关适配版本：

- **原始项目**：[`dwzhu-pku/PaperBanana`](https://github.com/dwzhu-pku/PaperBanana) 提出了多 Agent 自动学术插图生成流程。
- **原始论文**：[*PaperBanana: Automating Academic Illustration for AI Scientists*](https://huggingface.co/papers/2601.23265) 是方法和数据集来源。
- **中文化参考**：[`Mylszd/PaperBanana-CN`](https://github.com/Mylszd/PaperBanana-CN) 提供了中文界面与国内使用体验方向的参考。
- **本仓库贡献**：重构前端配置体验，增强 GPT/Gemini 中转站兼容，解耦 VLM 与文生图链路，支持 GPT-5.5、GPT-Image-2、Gemini 图文模型，并补充后台任务、导出回放、测试覆盖与错误隔离。

---

## 开源与使用限制

本仓库代码以 Apache-2.0 许可证发布。

请注意：PaperBanana 的核心多 Agent 学术绘图工作流由原作者在 Google 实习期间研发，相关工作流据原项目说明已涉及 Google 专利申请。请在商业用途前自行核查原项目说明、论文页面、许可证和专利限制。

---

## Citation

如果你的工作使用了 PaperBanana 方法或 PaperBananaBench，请优先引用原始 PaperBanana 论文与数据集。本仓库主要提供中文友好界面、模型网关适配和工程化增强。
