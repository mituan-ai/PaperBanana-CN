<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->

<p align="right">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/README.md">English</a> ·
  <strong>简体中文</strong>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/hero-zh.webp"
    width="100%"
    alt="PaperBanana-CN 科研生图工作台与生成的多模态故障诊断方法图"
  >
</p>

<p align="center">
  PaperBanana-CN 根据研究方法描述生成科研方法图，也可以根据 CSV 或 JSON 数据生成统计图。
  项目沿用 PaperBanana 的科研生图工作流，并增加 VLM 与图像模型独立连接、中文 Studio
  以及明确的宽高比和分辨率控制。
</p>

<p align="center">
  <a href="#快速开始"><img src="https://img.shields.io/badge/%E5%90%AF%E5%8A%A8_STUDIO-uvx_paperbanana--cn_studio-147862?style=for-the-badge&logo=gnometerminal&logoColor=white" alt="启动 Studio"></a>
  <a href="https://pypi.org/project/paperbanana-cn/"><img src="https://img.shields.io/badge/%E5%AE%89%E8%A3%85-PYPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white" alt="从 PyPI 安装"></a>
</p>

<p align="center">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mituan-ai/PaperBanana-CN/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=CI" alt="CI 状态"></a>
  <img src="https://img.shields.io/badge/Package-2.0.1-147862?style=flat-square" alt="软件包版本 2.0.1">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-52605B?style=flat-square" alt="MIT 许可证"></a>
</p>

## 从输入到成图的一次运行

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-workflow.gif"
    width="960"
    alt="PaperBanana-CN Studio 从输入参数到完成科研图的运行过程"
  >
</p>

这段录屏展示了一次方法图任务，从提交输入到得到最终结果。

## 开始前需要准备

运行环境需要 Python 3.10-3.12、[uv](https://docs.astral.sh/uv/) 和桌面浏览器。

| 任务 | 需要的模型连接 |
|---|---|
| 科研方法图 | VLM 和图像生成 |
| 统计图 | 仅 VLM |
| 多图组合与运行记录 | 不需要模型连接 |

每条连接分别填写协议、Base URL、API Key、模型名称和超时时间。VLM 与图像生成可以使用同一个
服务，也可以连接两个完全不同的服务。

## 快速开始

### 1. 启动 Studio

```bash
uvx paperbanana-cn studio
```

浏览器打开 <http://127.0.0.1:7860>。`uvx` 使用隔离环境运行，不会修改 Debian 或 Ubuntu
的系统 Python。

### 2. 添加模型连接

进入 **设置 → 视觉语言模型连接**，填写服务参数并选择 **保存并使用**。生成科研方法图前，
还需要在 **图像生成连接** 中完成相同操作。

编辑已经保存的连接不会自动启用它。API Key 留空会保留原有 Key，Studio 不会把已经保存的
Key 回填到浏览器。

<details>
<summary><strong>查看连接管理界面与协议说明</strong></summary>

<br>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/connections-zh.webp"
    width="100%"
    alt="PaperBanana-CN 视觉语言模型连接管理界面"
  >
</p>

[连接配置说明](https://github.com/mituan-ai/PaperBanana-CN/blob/main/docs/CONNECTIONS.md)
列出了支持的协议、凭据保存规则、连接测试和旧版兼容模式。

</details>

### 3. 生成图片

打开 **科研方法图**，填写方法内容和图注，选择宽高比、分辨率与输出格式，然后开始生成。

同一个任务也可以从命令行运行：

```bash
paperbanana-cn generate \
  --input method.txt \
  --caption "Overview of the proposed architecture" \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --format png
```

## PaperBanana-CN 的三项改动

### VLM 与图像生成分别连接

两条模型链路分别保存协议、Base URL、API Key、模型和超时时间。Studio、CLI 和 MCP 使用
同一组已保存连接。连接配置只保存凭据引用，API Key 不会写入仓库和运行 metadata。

项目支持官方接口、OpenAI-compatible 服务和 Gemini-compatible 服务。具体协议差异由
provider adapter 处理，不进入科研生图工作流。

### 中文与英文 Studio

Studio 的界面、帮助、校验、进度和错误信息提供中文与英文版本。切换界面语言不会修改 prompt、
论文内容或生成图片中的文字。

### 宽高比与分辨率

支持的宽高比：

`1:1` · `4:3` · `3:2` · `5:4` · `16:9` · `21:9` · `4:5` · `3:4` · `2:3` · `9:16`

分辨率档位：

`1K` · `2K` · `4K`

Studio 会在生成前显示实际请求尺寸或 provider 的原生档位。如果当前 adapter 不支持所选组合，
校验会停止请求并指出不支持的选项。

## Studio 功能

| 区域 | 功能 | 模型连接 |
|---|---|---|
| 生成 | 科研方法图 | VLM 和图像生成 |
| 生成 | 统计图 | VLM |
| 改进 | 继续运行 | 根据原任务决定 |
| 改进 | 质量评估 | VLM |
| 自动化 | 全文编排 | VLM 和图像生成 |
| 自动化 | 批处理 | 根据任务类型决定 |
| 自动化 | 参数扫描 | VLM 和图像生成 |
| 工具 | 多图组合 | 不需要 |
| 工具 | 运行记录 | 不需要 |

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-methodology-en.webp"
    width="100%"
    alt="PaperBanana-CN 科研方法图工作区与生成结果"
  >
</p>

<p align="center"><sub>科研方法图工作区，界面可切换为中文</sub></p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-statistical-plot-en.webp"
    width="100%"
    alt="PaperBanana-CN 统计图工作区与生成的折线图"
  >
</p>

<p align="center"><sub>统计图工作区，图中使用合成演示数据</sub></p>

## CLI、MCP、Docker 与 Colab

| 使用方式 | 命令或链接 |
|---|---|
| Studio | `paperbanana-cn studio` |
| CLI | `paperbanana-cn generate --help` |
| MCP Server | `paperbanana-cn mcp` |
| GitHub Action | [Action 使用说明](https://github.com/mituan-ai/PaperBanana-CN/blob/main/integrations/github-action/README.md) |
| Docker | `ghcr.io/mituan-ai/paperbanana-cn:2.0.1` |
| Colab | [快速开始 Notebook](https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb) |

<details>
<summary><strong>MCP 客户端配置</strong></summary>

```json
{
  "mcpServers": {
    "paperbanana-cn": {
      "command": "uvx",
      "args": ["paperbanana-cn", "mcp"]
    }
  }
}
```

MCP Server 提供 11 个工具，并读取 Studio 和 CLI 使用的同一组连接。工具清单和参数见
[MCP 使用说明](https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md)。

</details>

<details>
<summary><strong>Docker</strong></summary>

```bash
docker run --rm -p 7860:7860 \
  -v paperbanana-cn-config:/home/paperbanana/.config/paperbanana-cn \
  -v paperbanana-cn-data:/home/paperbanana/.local/share/paperbanana-cn \
  -v paperbanana-cn-outputs:/work/outputs \
  ghcr.io/mituan-ai/paperbanana-cn:2.0.1 \
  studio --host 0.0.0.0
```

</details>

<details>
<summary><strong>长期安装、源码运行与可选 provider</strong></summary>

在 uv 管理的隔离环境中安装命令：

```bash
uv tool install paperbanana-cn
paperbanana-cn studio
```

运行当前仓库源码：

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv sync
uv run paperbanana-cn studio
```

默认安装包含 Studio、MCP、PDF 输入、OpenAI-compatible 服务和 Gemini。

| 可选 adapter | 安装命令 |
|---|---|
| AWS Bedrock | `uv tool install "paperbanana-cn[bedrock]"` |
| Anthropic | `uv tool install "paperbanana-cn[anthropic]"` |
| LiteLLM | `uv tool install "paperbanana-cn[litellm]"` |
| 全部可选 provider | `uv tool install "paperbanana-cn[all-providers]"` |

在 CI 中可以使用 `paperbanana-cn connections add --api-key-env ENV_VAR`，让命令从环境变量读取
Key，避免把 Key 放进命令行参数。

</details>

## V1 与上游项目

V2 在 `main` 分支持续维护，发布名为 `paperbanana-cn`，Python 模块名为 `paperbanana_cn`，
唯一命令为 `paperbanana-cn`。

- [查看冻结的 `v1` 分支](https://github.com/mituan-ai/PaperBanana-CN/tree/v1)
- [下载 `v1.0.0` Release](https://github.com/mituan-ai/PaperBanana-CN/releases/tag/v1.0.0)

本项目的科研生图核心基于
[`llmsresearch/paperbanana`](https://github.com/llmsresearch/paperbanana)。PaperBanana-CN
是非官方社区实现，与上游作者不存在官方隶属或背书关系。

## 社区

PaperBanana-CN 由 [mituan](https://github.com/mituan-ai) 维护，采用
[MIT License](https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE)。

- 使用问题请发到 [Discussions](https://github.com/mituan-ai/PaperBanana-CN/discussions)。
- 可以复现的程序问题请发到 [Issues](https://github.com/mituan-ai/PaperBanana-CN/issues)。
- 安全问题请使用 [Private Vulnerability Reporting](https://github.com/mituan-ai/PaperBanana-CN/security/advisories/new)。
- 提交 Pull Request 前请阅读 [CONTRIBUTING.md](https://github.com/mituan-ai/PaperBanana-CN/blob/main/CONTRIBUTING.md)。

<details>
<summary><strong>开发检查</strong></summary>

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check paperbanana_cn/ mcp_server/ tests/ scripts/
```

请勿上传 API Key、私有中转站地址、未公开论文、私有数据集、本地连接存储或运行输出目录。

</details>

## Star 历史

<a href="https://www.star-history.com/?repos=mituan-ai%2FPaperBanana-CN&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&theme=dark&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
 </picture>
</a>
