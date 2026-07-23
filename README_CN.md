<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->

<p align="right">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/README.md">English</a> ·
  <strong>简体中文</strong>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/paperbanana_cn/studio/assets/paperbanana-cn-logo.jpg"
    width="104"
    alt="PaperBanana-CN Logo"
  >
</p>

<h1 align="center">PaperBanana-CN</h1>

<p align="center">
  <strong>用于生成、精修和管理科研图片的桌面生产工作台。</strong>
</p>

<p align="center">
  VLM 与图像模型独立连接 · 中文和英文 Studio · 统一的比例与分辨率控制
</p>

<p align="center">
  <a href="https://pypi.org/project/paperbanana-cn/"><img src="https://img.shields.io/pypi/v/paperbanana-cn?style=flat-square&logo=pypi&logoColor=white&color=147862" alt="PyPI 版本"></a>
  <a href="https://github.com/mituan-ai/PaperBanana-CN/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mituan-ai/PaperBanana-CN/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=CI" alt="CI 状态"></a>
  <img src="https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 到 3.12">
  <img src="https://img.shields.io/badge/Gradio-6.20.0-F97316?style=flat-square&logo=gradio&logoColor=white" alt="Gradio 6.20.0">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-2F6F61?style=flat-square" alt="MIT License"></a>
</p>

<p align="center">
  <a href="https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="在 Colab 中打开 PaperBanana-CN 快速入门"></a>
  <a href="https://github.com/mituan-ai/PaperBanana-CN/pkgs/container/paperbanana-cn"><img src="https://img.shields.io/badge/GHCR-paperbanana--cn-2496ED?style=flat-square&logo=docker&logoColor=white" alt="GHCR 容器"></a>
  <a href="https://registry.modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-11_tools-147862?style=flat-square" alt="包含 11 个工具的 MCP Server"></a>
</p>

<p align="center">
  开发者：<a href="https://github.com/mituan-ai">mituan</a>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-methodology-en.webp"
    width="100%"
    alt="PaperBanana-CN Studio 正在生成 16:9 科研方法图"
  >
</p>

<p align="center"><sub>脱敏的 Studio 预览，不包含凭据或私有接口地址。</sub></p>

## V2 增加了什么

| | 能力 | 对用户的实际作用 |
|---|---|---|
| 🔌 | **两条模型链路独立配置** | VLM 与图像生成可以使用不同的协议、Base URL、API Key、模型和超时时间。 |
| 🌐 | **官方接口与兼容中转站** | 复用现有 OpenAI-compatible、Gemini、OpenRouter 和 Bedrock 适配器，不硬编码中转站域名。 |
| 🇨🇳 | **中文和英文 Studio** | 在同一个 Studio 页面中切换语言，不修改 Prompt、论文内容或图中标签语言。 |
| 📐 | **一套尺寸系统** | 统一选择 10 种比例和 `1K` / `2K` / `4K`，不支持的组合在付费请求前失败。 |
| 🔐 | **连接凭据与项目隔离** | Key 保存在仓库外，不回填浏览器，也不会进入运行 metadata。 |
| 🧰 | **所有入口共享配置** | Studio、CLI 和 MCP 使用相同的当前 VLM/image 连接。 |

PaperBanana-CN 保留上游的检索、规划、候选生成、评审、精修、统计图、任务恢复、批处理、
全文编排和矢量导出工作流。V2 只重建连接、中文界面和图片尺寸这三个产品边界，不复制
科研生图核心流程。

## 快速开始

### 无需长期安装，直接启动 Studio

需要 Python 3.10-3.12 和桌面浏览器。最短启动方式：

```bash
uvx paperbanana-cn studio
```

浏览器打开 <http://127.0.0.1:7860>。界面默认中文，可在**设置**中切换为英文。

### 长期安装命令

使用 `uv`：

```bash
uv tool install paperbanana-cn
paperbanana-cn studio
```

或安装到独立虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install paperbanana-cn
paperbanana-cn studio
```

Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。

默认包已经包含 Studio、MCP、OpenAI-compatible 与 Gemini 适配器，以及 PDF 输入。
只有额外 provider 需要安装 extras：

| Extra | 安装命令 | 增加的能力 |
|---|---|---|
| Bedrock | `pip install "paperbanana-cn[bedrock]"` | AWS Bedrock VLM 和图像适配器 |
| Anthropic | `pip install "paperbanana-cn[anthropic]"` | Anthropic VLM 适配器 |
| LiteLLM | `pip install "paperbanana-cn[litellm]"` | LiteLLM 路由 |
| 全部可选 provider | `pip install "paperbanana-cn[all-providers]"` | 上述三个 extra |

## 配置两条模型链路

通常直接在 Studio 中完成：

1. 打开**设置 → 视觉语言模型连接**。
2. 填写连接名称、协议、Base URL、准确的模型名称、超时时间和 API Key。
3. 点击**保存并使用**。
4. 在**图像生成连接**中重复上述操作。
5. 返回**科研方法图**，选择比例和分辨率后开始生成。

浏览或编辑连接不会自动启用它。Key 输入框留空会保留原 Key；清除 Key 是单独的确认操作。

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/connections-zh.webp"
    width="100%"
    alt="中文连接管理页展示独立 VLM 连接字段"
  >
</p>

自动化场景可以在不把 Key 放进命令行参数的情况下创建连接：

```bash
export VLM_API_KEY
export IMAGE_API_KEY

paperbanana-cn connections add \
  --role vlm \
  --name "Primary VLM" \
  --provider openai \
  --base-url "https://vlm.example.com/v1" \
  --model "your-vlm-model" \
  --api-key-env VLM_API_KEY

paperbanana-cn connections add \
  --role image \
  --name "Primary image" \
  --provider openai_imagen \
  --base-url "https://image.example.com/v1" \
  --model "your-image-model" \
  --size-mode explicit_pixels \
  --api-key-env IMAGE_API_KEY
```

连接存储位置、协议、连接测试和显式 legacy 模式见
[连接配置文档](https://github.com/mituan-ai/PaperBanana-CN/blob/main/docs/CONNECTIONS.md)。

## 使用 CLI 生成

启用两条连接后：

```bash
paperbanana-cn generate \
  --input method.txt \
  --caption "Overview of the proposed architecture" \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --format png
```

统计图只需要当前 VLM 连接：

```bash
paperbanana-cn plot \
  --data results.csv \
  --intent "Compare model performance across settings" \
  --aspect-ratio 4:3 \
  --vector
```

使用 `paperbanana-cn --help` 查看全部命令。

## Studio 工作流

| 工作流 | 所需连接 | 输出 |
|---|---|---|
| **科研方法图** | VLM + 图像模型 | 生成并精修科研方法示意图 |
| **统计图** | VLM | 从 CSV 或 JSON 确定性渲染统计图 |
| **继续运行** | 根据原 run 决定 | 继续精修方法图或统计图 |
| **质量评估** | VLM | 现有四维质量评价 |
| **全文编排** | VLM + 图像模型 | 从论文规划并生成多图包 |
| **批处理** | 根据批任务类型决定 | 方法图或统计图批处理报告 |
| **参数扫描** | VLM + 图像模型 | 排序后的参数变体 |
| **多图组合** | 无 | 确定性多面板图片 |
| **运行记录** | 无 | 浏览 run、迭代、metadata 和结果 |

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-statistical-plot-en.webp"
    width="100%"
    alt="PaperBanana-CN Studio 根据 CSV 数据渲染统计折线图"
  >
</p>

## 比例与分辨率

全局统一的比例集合：

`1:1` · `4:3` · `3:2` · `5:4` · `16:9` · `21:9` · `4:5` · `3:4` · `2:3` · `9:16`

图像生成使用统一的 `1K`、`2K` 和 `4K` 语义。每个图像适配器会声明自己接受原生档位、
明确像素、固定预设还是 Prompt 提示。Studio 会显示实际请求像素或原生档位。
PaperBanana-CN 不会静默裁切、拉伸或替换不支持的比例。

统计图和矢量导出继续使用各自的确定性尺寸路径。

## MCP

PaperBanana-CN 在同一个包中提供 11 个现有的生成、统计图、评价、继续运行、全文编排、
批处理和参考图工具，不需要安装独立 MCP 包。

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

MCP 使用与 Studio、CLI 相同的当前连接。完整工具契约见
[MCP 文档](https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md)。

## Colab、GitHub Action 与 Docker

### Colab

[PaperBanana-CN Quickstart](https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb)
提供干净的云端入门环境。Notebook 安装正式发布的 `paperbanana-cn`，不包含执行输出或凭据。

### GitHub Action

正式维护的组合 Action 支持独立的 VLM/image URL、Key、Model、比例和分辨率：

```yaml
- uses: mituan-ai/PaperBanana-CN/integrations/github-action@v2.0.1
  with:
    tex-file: sections/method.tex
    caption: "Overview of our proposed framework"
    vlm-model: ${{ vars.VLM_MODEL }}
    vlm-api-key: ${{ secrets.VLM_API_KEY }}
    image-model: ${{ vars.IMAGE_MODEL }}
    image-api-key: ${{ secrets.IMAGE_API_KEY }}
    aspect-ratio: "16:9"
    resolution: "2K"
```

完整 provider 和输出参数见
[Action 文档](https://github.com/mituan-ai/PaperBanana-CN/blob/main/integrations/github-action/README.md)。

### Docker

```bash
docker pull ghcr.io/mituan-ai/paperbanana-cn:2.0.1

docker run --rm -p 7860:7860 \
  -v paperbanana-cn-config:/home/paperbanana/.config/paperbanana-cn \
  -v paperbanana-cn-data:/home/paperbanana/.local/share/paperbanana-cn \
  -v paperbanana-cn-outputs:/work/outputs \
  ghcr.io/mituan-ai/paperbanana-cn:2.0.1 \
  studio --host 0.0.0.0
```

镜像使用非 root 用户运行，ENTRYPOINT 为 `paperbanana-cn`。

## 包名与兼容性

| 入口 | V2 名称 |
|---|---|
| PyPI 分发名 | `paperbanana-cn` |
| Python 导入名 | `paperbanana_cn` |
| 终端命令 | `paperbanana-cn` |
| MCP 命令 | `paperbanana-cn mcp` |
| MCP Registry | `io.github.mituan-ai/paperbanana-cn` |

独立的模块名和命令名使 V2 可以与上游包安装在同一个环境中。现有 `PAPERBANANA_*`
环境变量只在显式 legacy 配置中继续使用。

## V1 归档

V2 在 `main` 维护，旧实现已经冻结：

- [浏览 `v1` 分支](https://github.com/mituan-ai/PaperBanana-CN/tree/v1)
- [下载 `v1.0.0` Release](https://github.com/mituan-ai/PaperBanana-CN/releases/tag/v1.0.0)

V1 与 V2 的 Git 历史相互独立，V1 不再继续开发。

## 开发与反馈

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest tests/ -q
```

- 使用问题请进入
  [Discussions](https://github.com/mituan-ai/PaperBanana-CN/discussions)。
- 可复现问题请提交到
  [Issues](https://github.com/mituan-ai/PaperBanana-CN/issues)。
- 安全漏洞请通过
  [Private Vulnerability Reporting](https://github.com/mituan-ai/PaperBanana-CN/security/advisories/new)
  私密提交。
- 提交代码前请阅读
  [CONTRIBUTING.md](https://github.com/mituan-ai/PaperBanana-CN/blob/main/CONTRIBUTING.md)。

不得上传 API Key、私有中转站 URL、未公开论文、私有数据集、连接存储文件或运行目录。

## 许可证与上游归属

PaperBanana-CN 使用
[MIT License](https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE)。
科研生图核心基于
[`llmsresearch/paperbanana`](https://github.com/llmsresearch/paperbanana)。
PaperBanana-CN 是由 mituan 维护的非官方社区实现，与上游作者不存在隶属或官方合作关系。

## Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=mituan-ai/PaperBanana-CN&type=Date)](https://star-history.com/#mituan-ai/PaperBanana-CN&Date)
