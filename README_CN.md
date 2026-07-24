<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->

<p align="right">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/README.md">English</a> ·
  <strong>简体中文</strong>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/hero-zh.webp"
    width="100%"
    alt="PaperBanana-CN 科研生图工作台与真实生成的多模态故障诊断图"
  >
</p>

<p align="center">
  <a href="#60-秒开始使用"><img src="https://img.shields.io/badge/%E5%90%AF%E5%8A%A8_STUDIO-uvx_paperbanana--cn_studio-147862?style=for-the-badge&logo=gnometerminal&logoColor=white" alt="启动 Studio"></a>
  <a href="https://pypi.org/project/paperbanana-cn/"><img src="https://img.shields.io/badge/%E5%AE%89%E8%A3%85-PYPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white" alt="从 PyPI 安装"></a>
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md"><img src="https://img.shields.io/badge/%E8%BF%9E%E6%8E%A5-11_%E4%B8%AA_MCP_%E5%B7%A5%E5%85%B7-52605B?style=for-the-badge" alt="通过 MCP 连接"></a>
  <a href="https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb"><img src="https://img.shields.io/badge/%E4%BD%93%E9%AA%8C-COLAB-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white" alt="在 Colab 中体验"></a>
</p>

<p align="center">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mituan-ai/PaperBanana-CN/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=CI" alt="CI 状态"></a>
  <img src="https://img.shields.io/badge/Package-2.0.1-147862?style=flat-square" alt="Package 版本 2.0.1">
  <img src="https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 到 3.12">
  <img src="https://img.shields.io/badge/Gradio-6.20.0-F97316?style=flat-square&logo=gradio&logoColor=white" alt="Gradio 6.20.0">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-52605B?style=flat-square" alt="MIT License"></a>
</p>

<p align="center">
  <strong>把方法描述和研究数据直接变成科研示意图与统计图。</strong><br>
  保留 PaperBanana 工作流，自由选择 VLM、图像服务、界面语言、宽高比和分辨率。
</p>

## 看一次真实运行

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-workflow.gif"
    width="960"
    alt="PaperBanana-CN Studio 从配置输入、运行阶段到完成科研图的全过程"
  >
</p>

<p align="center">
  <sub>一次真实 Studio 运行：配置输入 → 实时流程阶段 → 完成结果。画面不包含凭据或私有服务地址。</sub>
</p>

## 真实产出，不是示意占位

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/showcase-zh.webp"
    width="100%"
    alt="PaperBanana-CN 生成的科研方法图、精修概念图和统计图"
  >
</p>

科研方法图由已配置的 VLM 与图像模型完成生成和精修。统计图沿用 PaperBanana 的确定性
绘图路径，其中的数值是专门构造的演示数据。

## V2 真正新增了什么

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/capabilities-zh.svg"
    width="100%"
    alt="PaperBanana-CN V2 新增双模型独立连接、中英文 Studio 和精确输出尺寸控制"
  >
</p>

| 双模型链路独立配置 | 完整的中英文 Studio | 精确控制最终输出 |
|---|---|---|
| VLM 与图像生成分别设置协议、Base URL、API Key、模型名称和超时时间。 | 界面可在中文和英文之间切换，但不会改写 Prompt、论文内容或图中标签。 | 选择 10 种宽高比和 `1K` / `2K` / `4K`；不支持的组合会在付费图像请求前失败。 |

Studio、CLI 和 MCP 共用同一组已保存连接。API Key 保存在仓库外，不会回填到浏览器，
也不会进入运行 metadata。

## 60 秒开始使用

### 1. 启动桌面 Studio

需要 Python 3.10-3.12、[uv](https://docs.astral.sh/uv/) 和桌面浏览器：

```bash
uvx paperbanana-cn studio
```

浏览器打开 <http://127.0.0.1:7860>。`uvx` 使用独立环境，不会修改 Debian 或 Ubuntu
的系统 Python。

### 2. 连接两个模型角色

打开**设置 → 视觉语言模型连接**，填写协议、Base URL、API Key、准确的模型名称和
超时时间，然后选择**保存并使用**。在**图像生成连接**中重复一次。

> [!TIP]
> 两个角色既可以使用同一中转站，也可以使用完全不同的服务。编辑已保存连接不会
> 自动启用它，Key 输入框留空会保留原有 Key。

<details>
<summary><strong>查看连接管理界面</strong></summary>

<br>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/connections-zh.webp"
    width="100%"
    alt="PaperBanana-CN 连接管理器中的独立视觉语言模型服务字段"
  >
</p>

支持的协议、凭据存储、连接测试和显式 legacy 模式见
[连接配置文档](https://github.com/mituan-ai/PaperBanana-CN/blob/main/docs/CONNECTIONS.md)。

</details>

### 3. 开始生成

进入**科研方法图**，填写方法内容和表达意图，选择宽高比与分辨率后运行。结果画布会
把最终图片、真实输出尺寸、迭代历史和下载操作放在一起。

同一任务也可以通过 CLI 运行：

```bash
paperbanana-cn generate \
  --input method.txt \
  --caption "Overview of the proposed architecture" \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --format png
```

## 围绕结果设计的工作台

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-tour-zh.webp"
    width="100%"
    alt="带标注的 PaperBanana-CN Studio，展示任务输入、尺寸控制和结果画布"
  >
</p>

| 区域 | 工作流 | 所需连接 |
|---|---|---|
| **生成** | 科研方法图、统计图 | VLM + 图像模型 / 仅 VLM |
| **改进** | 继续运行、质量评估 | 根据 run 决定 / 仅 VLM |
| **自动化** | 全文编排、批处理、参数扫描 | 根据任务决定 |
| **工具** | 多图组合、运行记录 | 无 |

任务输入集中在左侧工作区，结果画布始终是视觉中心。运行完成后日志会自动收起；运行
失败时保留全部输入，并直接显示可操作的错误信息。

## 只有一套科研工作流

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/workflow-zh.svg"
    width="100%"
    alt="独立的 VLM 与图像生成连接进入现有科研生图流程"
  >
</p>

PaperBanana-CN 不维护第二套科研流程。检索、规划、候选生成、评审、精修、确定性统计图、
任务恢复、批处理、全文编排和矢量导出仍沿用上游 PaperBanana 工作流。

## 选择适合你的入口

| 入口 | 适合场景 | 从这里开始 |
|---|---|---|
| **Studio** | 交互式生图与连接管理 | `paperbanana-cn studio` |
| **CLI** | 可复现的本地运行与脚本 | `paperbanana-cn generate --help` |
| **MCP** | 在 MCP 客户端中调用 11 个科研图片工具 | `paperbanana-cn mcp` |
| **GitHub Action** | 在仓库工作流内生成图片 | [Action 文档](https://github.com/mituan-ai/PaperBanana-CN/blob/main/integrations/github-action/README.md) |
| **Docker** | 固定且隔离的运行环境 | `ghcr.io/mituan-ai/paperbanana-cn:2.0.1` |
| **Colab** | 在云端 Notebook 中体验 | [快速入门](https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb) |

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

MCP Server 使用与 Studio、CLI 相同的当前连接。全部 11 个工具及参数见
[MCP 文档](https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md)。

</details>

<details>
<summary><strong>Docker 启动命令</strong></summary>

```bash
docker run --rm -p 7860:7860 \
  -v paperbanana-cn-config:/home/paperbanana/.config/paperbanana-cn \
  -v paperbanana-cn-data:/home/paperbanana/.local/share/paperbanana-cn \
  -v paperbanana-cn-outputs:/work/outputs \
  ghcr.io/mituan-ai/paperbanana-cn:2.0.1 \
  studio --host 0.0.0.0
```

</details>

## 输出尺寸清楚、可预期

**宽高比**

`1:1` · `4:3` · `3:2` · `5:4` · `16:9` · `21:9` · `4:5` · `3:4` · `2:3` · `9:16`

**分辨率档位**

`1K` · `2K` · `4K`

每个图像适配器会声明自己接受原生档位、明确像素、固定预设还是 Prompt 提示。Studio
会显示实际请求尺寸或原生档位，不会静默裁切、拉伸或替换不支持的比例。

<details>
<summary><strong>长期安装、源码运行与可选 Provider</strong></summary>

将命令安装到 uv 管理的独立环境：

```bash
uv tool install paperbanana-cn
paperbanana-cn studio
```

运行当前源码：

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv sync
uv run paperbanana-cn studio
```

默认包已包含 Studio、MCP、PDF 输入、OpenAI-compatible 服务和 Gemini。

| 可选适配器 | 安装命令 |
|---|---|
| AWS Bedrock | `uv tool install "paperbanana-cn[bedrock]"` |
| Anthropic | `uv tool install "paperbanana-cn[anthropic]"` |
| LiteLLM | `uv tool install "paperbanana-cn[litellm]"` |
| 全部可选 Provider | `uv tool install "paperbanana-cn[all-providers]"` |

在 CI 中应从环境变量读取凭据，不要把 Key 放在命令行值里：

```bash
paperbanana-cn connections add \
  --role vlm \
  --name "Primary VLM" \
  --provider openai \
  --base-url "https://vlm.example.com/v1" \
  --model "your-vlm-model" \
  --api-key-env VLM_API_KEY
```

</details>

## 保留 V1，继续推进 V2

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/lineage-zh.svg"
    width="100%"
    alt="PaperBanana-CN V1 已冻结，V2 在 main 分支持续维护"
  >
</p>

V2 在 `main` 维护，对应 `paperbanana-cn` 分发包、`paperbanana_cn` Python 模块和
`paperbanana-cn` 命令。V1 作为历史版本完整保留：

- [浏览独立的 `v1` 分支](https://github.com/mituan-ai/PaperBanana-CN/tree/v1)
- [下载 `v1.0.0` Release](https://github.com/mituan-ai/PaperBanana-CN/releases/tag/v1.0.0)

## 项目与社区

PaperBanana-CN 由 [mituan](https://github.com/mituan-ai) 维护。

- 使用问题请进入 [Discussions](https://github.com/mituan-ai/PaperBanana-CN/discussions)。
- 可复现问题请提交到 [Issues](https://github.com/mituan-ai/PaperBanana-CN/issues)。
- 安全漏洞请通过 [Private Vulnerability Reporting](https://github.com/mituan-ai/PaperBanana-CN/security/advisories/new) 私密提交。
- 提交代码前请阅读 [CONTRIBUTING.md](https://github.com/mituan-ai/PaperBanana-CN/blob/main/CONTRIBUTING.md)。

PaperBanana-CN 使用
[MIT License](https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE)，科研生图核心
基于 [`llmsresearch/paperbanana`](https://github.com/llmsresearch/paperbanana)。
这是一个非官方社区实现，与上游作者不存在隶属或官方合作关系。

<details>
<summary><strong>开发检查</strong></summary>

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check paperbanana_cn/ mcp_server/ tests/ scripts/
```

不得上传 API Key、私有中转站 URL、未公开论文、私有数据集、本地连接存储或运行目录。

</details>

## Star 历史

<a href="https://www.star-history.com/?repos=mituan-ai%2FPaperBanana-CN&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&theme=dark&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
 </picture>
</a>
