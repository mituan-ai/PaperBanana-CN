<p align="center">
  <img src="assets/hero_banner.png" alt="PaperBanana-Pro" width="420">
</p>

<h1 align="center">PaperBanana-Pro · 纸香蕉</h1>

<p align="center">
  <strong>面向未来的工业级学术绘图引擎</strong><br>
  多 Agent 协同 · 全中文流式交互 · 深度精修闭环
</p>

<p align="center">
  <a href="https://github.com/917940234/PaperBanana-Pro/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="License"></a>&nbsp;
  <img src="https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white" alt="Python">&nbsp;
  <a href="https://github.com/917940234/PaperBanana-Pro/actions"><img src="https://img.shields.io/github/actions/workflow/status/917940234/PaperBanana-Pro/ci.yml?label=CI&logo=github" alt="CI"></a>&nbsp;
  <img src="https://img.shields.io/badge/GPT%20%2B%20Gemini-Gateway%20Ready-8A2BE2" alt="GPT and Gemini Gateway Ready">&nbsp;
  <img src="https://img.shields.io/badge/version-0.1.0-brightgreen" alt="Version">
  <br>
  <a href="https://huggingface.co/datasets/dwzhu/PaperBananaBench"><img src="https://img.shields.io/badge/🤗_Dataset-PaperBananaBench-yellow" alt="Dataset"></a>&nbsp;
  <a href="https://huggingface.co/papers/2601.23265"><img src="https://img.shields.io/badge/📄_Paper-HuggingFace-orange" alt="Paper"></a>&nbsp;
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome">
</p>

---

## 👑 为什么选择 Pro？

PaperBanana-Pro 在 [原始 PaperBanana](https://github.com/dwzhu-pku/PaperBanana) 基础上独立演化，并吸收中文化交互与轻量检索经验，继续完成产品化、工程化与中转站兼容增强。本 fork 重点强化 **GPT / Gemini 双通道中转站兼容**：VLM 文本与文生图可以分别选择 GPT 或 Gemini，并分别配置 API Key、Base URL 和模型名称，适合使用 OpenAI-compatible / Gemini-compatible gateway 的科研工作流。

| | 特性 | 说明 |
|---|---|---|
| 🚀 | **流式高并发生成** | 后台异步作业队列 + 实时事件时间线，支持 40+ 候选并发，界面永不卡死 |
| 📦 | **Bundle 便携式交付** | 独创 `Bundle v1` 架构，一个 `.bundle.json` 还原完整图文时间线和评审记录 |
| 🛡️ | **智能容灾重试** | Pro→Flash 模型梯队平滑降级，确定性任务状态，真正的工程健壮性 |
| 🎨 | **2K/4K 精修工作台** | 独立精修闭环，支持并发多版本重绘、树状演化链和版本回退 |
| 🇨🇳 | **全中文产品界面** | 从输入到输出全中文，侧边栏参数人性化，即开即用 |
| 🔧 | **注册制流水线** | Pipeline Registry 驱动，告别硬编码分支，一行配置扩展新流程 |
| 📊 | **Plot 全链路** | 数据输入解析 → 代码生成 → 本地重渲染 → 精修，统计图端到端闭环 |
| ⚡ | **`uv` 一键安装** | `uv tool install` 全局可用，免虚拟环境、免 PATH 配置 |
| 🔌 | **GPT / Gemini 中转站兼容** | VLM 文本与文生图双链路解耦，GPT/Gemini 可任意组合，分别配置 API Key、Base URL 和模型名 |
| 🧩 | **自定义模型供应商** | 支持 OpenAI-compatible API，填入 Base URL 即可接入自有或第三方模型服务 |

---

## ✨ 核心工作流

<table>
<tr>
<td width="50%">

**📋 生成候选方案**

输入论文方法章节和图注，一键并发生成多个科研插图候选。

<img src="assets/ui_generation_workspace.png" alt="生成候选" width="100%">
</td>
<td width="50%">

**🎯 候选决策 & 批量导出**

收藏、选定或淘汰候选方案，一键 ZIP 打包下载全部结果。

<img src="assets/ui_candidate_results.png" alt="候选决策" width="100%">
</td>
</tr>
<tr>
<td width="50%">

**🔍 流水线演化追踪**

展开任意候选方案的演化时间线，逐阶段查看规划→风格增强→评审修正的完整过程。

<img src="assets/ui_pipeline_detail.png" alt="流水线详情" width="100%">
</td>
<td width="50%">

**✨ 2K/4K 图像精修**

独立精修工作台，设置目标分辨率与宽高比，每轮精修形成版本链，可从任意历史版本继续或回退。

<img src="assets/ui_refine_workspace.png" alt="图像精修" width="100%">
</td>
</tr>
</table>

<details>
<summary>📸 <strong>更多功能截图</strong>（点击展开）</summary>

<br>

**启动前检查与参数预览** — 自动校验配置并预估成本

<img src="assets/ui_preflight_check.png" alt="预检" width="60%">

**历史回放** — 从 Bundle 快照中载入过往运行结果

<img src="assets/ui_history_replay.png" alt="历史回放" width="60%">

**批量下载** — 按筛选范围一键打包 ZIP（含图像、描述、绘图代码）

<img src="assets/ui_batch_download.png" alt="批量下载" width="60%">

**API Key 可视化配置** — 密钥自动存储到本地，刷新不丢失

<img src="assets/ui_api_key_config.png" alt="API Key 配置" width="40%">

**自定义模型供应商** — 接入任意 OpenAI 兼容 API，填写 Base URL 和 Key 即可使用

<img src="assets/自定义供应商.png" alt="自定义模型供应商" width="40%">

</details>

---

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/917940234/PaperBanana-Pro.git
cd PaperBanana-Pro
uv python install 3.12
uv sync --locked
uv tool install --editable . --force
```

安装完成后，`paperbanana` 命令可在任意目录使用。如未进入 PATH，执行 `uv tool update-shell` 即可。

> [!TIP]
> 不需要全局命令？也可以直接 `streamlit run demo.py` 启动 GUI，或 `python main.py --help` 使用 CLI。

### 2. 准备数据集（可选，强烈推荐）

下载 [`dwzhu/PaperBananaBench`](https://huggingface.co/datasets/dwzhu/PaperBananaBench) 并放到 `data/PaperBananaBench/` 下。该数据集提供 few-shot 参考样例和评估基准。

如果只是试用，可将检索设置为 `none` 跳过数据集依赖。

### 3. 配置 API Key 与中转站

推荐使用环境变量或本地 `configs/local/*.txt` 保存密钥，不要把真实 Key 写进 Git。也可以复制模板后只填写非敏感默认模型名和 Base URL：

```bash
cp configs/model_config.template.yaml configs/model_config.yaml
```

本 fork 支持把 **VLM 文本** 与 **文生图** 分成两条独立链路。每条链路都可以在 GUI 中选择 GPT 或 Gemini，并分别填写 API Key、Base URL 和模型名。

常用环境变量如下：

| 链路 | GPT / OpenAI-compatible | Gemini-compatible |
| --- | --- | --- |
| VLM Key | `PAPERBANANA_OPENAI_VLM_API_KEY` | `PAPERBANANA_GEMINI_VLM_API_KEY` |
| 文生图 Key | `PAPERBANANA_OPENAI_IMAGE_API_KEY` | `PAPERBANANA_GEMINI_IMAGE_API_KEY` |
| Base URL | `PAPERBANANA_OPENAI_BASE_URL`，通常形如 `https://gateway.example.com/v1` | `PAPERBANANA_GEMINI_BASE_URL`，通常形如 `https://gateway.example.com` |
| VLM 模型 | `PAPERBANANA_OPENAI_VLM_MODEL` | `PAPERBANANA_GEMINI_VLM_MODEL` |
| 文生图模型 | `PAPERBANANA_OPENAI_IMAGE_MODEL` | `PAPERBANANA_GEMINI_IMAGE_MODEL` |

当前内置 Provider：**GPT / OpenAI**、**Gemini**、**OpenRouter** 和 **Evolink**。

您也可以直接在 GUI 中可视化配置，API Key 会自动存储到本地：

<img src="assets/ui_api_key_config.png" alt="API Key 配置" width="280">

### 4. 启动

```bash
paperbanana          # 等价于 paperbanana gui，会在 8501 端口启动前端
```

---

## 📖 使用指南

### GUI — 主产品界面

```bash
paperbanana gui
```

提供两个核心工作区：

- **生成候选方案**：`diagram`（科研插图）或 `plot`（统计图），支持后台生成、多候选并发、实时预览、历史回放、批量导出
- **精修图像**：对候选结果做修改、放大，支持版本历史、并发精修、批量下载

### CLI — 批处理

```bash
paperbanana run --task_name diagram --exp_mode demo_full --provider gemini
```

适合数据集批量运行与产物归档。常用参数：

| 参数 | 说明 |
| --- | --- |
| `--task_name` | `diagram` 或 `plot` |
| `--exp_mode` | 流水线模式，如 `demo_full`、`demo_planner_critic` |
| `--provider` | `gemini` / `openai` / `openrouter` / `evolink` |
| `--max_critic_rounds` | 最大评审轮数，可设为 `0` |
| `--retrieval_setting` | 检索模式：`auto`、`curated`、`none` 等 |
| `--resume` | 自动恢复上次运行 |

完整参数见 `paperbanana run --help`。

### Viewer — 结果审阅

```bash
paperbanana viewer evolution   # 查看流程演化
paperbanana viewer eval        # 查看带参考结果的评估
```

---

## 🏗️ 架构

![PaperBanana-Pro 流水线](assets/method_diagram.png)

| 阶段 | 作用 |
| --- | --- |
| Retriever | 从参考池中检索 few-shot 样例 |
| Planner | 生成结构化的可视化描述 |
| Stylist | 优化学术表达和风格一致性 |
| Visualizer | 生成图像（diagram）或 Matplotlib 代码（plot） |
| Critic | 多轮评审与修订建议 |
| Polish | 可选后处理精修 |

---

## 📁 项目结构

```text
PaperBanana-Pro/
├── agents/          # 多 Agent 阶段实现
├── configs/         # 模型与 API Key 配置
├── data/            # 数据集目录
├── visualize/       # Streamlit Viewer
├── cli.py           # 全局命令入口
├── demo.py          # GUI 主程序
├── main.py          # CLI 批处理入口
└── pyproject.toml   # 项目元数据与依赖
```

## 🗺️ 路线图

- [ ] 多语言 UI 与提示词支持
- [ ] 扩展更多会议数据集（ICML、ACL 等），适应不同会议风格
- [ ] 精修功能扩展：迭代流程引入精修功能
- [ ] Plot 结构化合同与自动修复（`PlotSpec`）
- [ ] 无参考自动质量评估（No-reference QA）
- [ ] 发布到 PyPI，支持 `uv tool install paperbanana-pro`

---

## 🙏 致谢与项目关系

本项目是面向开源使用的 PaperBanana-Pro fork，建立在以下工作基础上：

- **原始 PaperBanana**：[`dwzhu-pku/PaperBanana`](https://github.com/dwzhu-pku/PaperBanana) 提出了多 Agent 自动学术插图生成流程，并发布了 PaperBananaBench。
- **原始论文**：[*PaperBanana: Automating Academic Illustration for AI Scientists*](https://huggingface.co/papers/2601.23265) 是本项目方法论和基准数据的源头。
- **中文化与产品化参考**：[`Mylszd/PaperBanana-CN`](https://github.com/Mylszd/PaperBanana-CN) 提供了中文界面和轻量检索方向的参考。
- **PaperBanana-Pro 贡献**：在原始项目基础上扩展了 Streamlit 工作台、后台并发作业、历史回放、Bundle 导出、多轮评审精修、Plot 工作流、`uv` 安装与更完整的测试覆盖。
- **本 fork 的新增亮点**：重点实现 GPT / Gemini 双 Provider 中转站兼容，VLM 文本与文生图两条链路完全解耦，支持分别选择 GPT 或 Gemini，并分别配置模型名、API Key 与 Base URL；同时修复前端状态串线、图像客户端误用文本客户端等网关场景下的关键问题。

## 📄 License

Apache-2.0

## ⚠️ 专利与商用限制

PaperBanana 的核心方法论（多 Agent 学术绘图流水线）由原作者在 Google 实习期间研发，**Google 已就相关工作流申请了专利**。这意味着 PaperBanana 的流水线逻辑 **不得用于商业用途**。PaperBanana-Pro 作为在原始项目基础上的独立演化版本，同样受此限制约束。请在使用时知悉。
