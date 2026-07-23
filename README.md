<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->

<p align="right">
  <strong>English</strong> ·
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/README_CN.md">简体中文</a>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/paperbanana_cn/studio/assets/paperbanana-cn-logo.jpg"
    width="104"
    alt="PaperBanana-CN logo"
  >
</p>

<h1 align="center">PaperBanana-CN</h1>

<p align="center">
  <strong>A desktop workbench for generating, refining, and managing scientific figures.</strong>
</p>

<p align="center">
  Independent VLM and image connections · Chinese and English Studio ·
  unified aspect ratio and resolution controls
</p>

<p align="center">
  <a href="https://pypi.org/project/paperbanana-cn/"><img src="https://img.shields.io/pypi/v/paperbanana-cn?style=flat-square&logo=pypi&logoColor=white&color=147862" alt="PyPI version"></a>
  <a href="https://github.com/mituan-ai/PaperBanana-CN/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mituan-ai/PaperBanana-CN/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=CI" alt="CI status"></a>
  <img src="https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 to 3.12">
  <img src="https://img.shields.io/badge/Gradio-6.20.0-F97316?style=flat-square&logo=gradio&logoColor=white" alt="Gradio 6.20.0">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-2F6F61?style=flat-square" alt="MIT License"></a>
</p>

<p align="center">
  <a href="https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open the PaperBanana-CN Quickstart in Colab"></a>
  <a href="https://github.com/mituan-ai/PaperBanana-CN/pkgs/container/paperbanana-cn"><img src="https://img.shields.io/badge/GHCR-paperbanana--cn-2496ED?style=flat-square&logo=docker&logoColor=white" alt="GHCR container"></a>
  <a href="https://registry.modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-11_tools-147862?style=flat-square" alt="MCP server with 11 tools"></a>
</p>

<p align="center">
  Developed by <a href="https://github.com/mituan-ai">mituan</a>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-methodology-en.webp"
    width="100%"
    alt="PaperBanana-CN Studio generating a 16:9 scientific methodology diagram"
  >
</p>

<p align="center"><sub>Sanitized Studio preview; no credentials or private endpoints are shown.</sub></p>

## What V2 adds

| | Capability | What it changes for the user |
|---|---|---|
| 🔌 | **Independent model connections** | The VLM and image generator can use different protocols, Base URLs, API keys, model names, and timeouts. |
| 🌐 | **Official APIs and compatible relays** | Reuse the existing OpenAI-compatible, Gemini, OpenRouter, and Bedrock adapters without hard-coded relay domains. |
| 🇨🇳 | **Chinese and English Studio** | Switch the interface language in one Studio page without changing prompts, paper content, or figure labels. |
| 📐 | **One size system** | Select any of 10 aspect ratios and `1K` / `2K` / `4K`; unsupported combinations fail before a paid request. |
| 🔐 | **Private connection storage** | API keys stay outside the repository, are never filled back into the browser, and are excluded from run metadata. |
| 🧰 | **Shared configuration** | Studio, CLI, and MCP use the same active VLM and image profiles. |

PaperBanana-CN retains the upstream retrieval, planning, candidate generation, critique, refinement,
statistical plotting, task recovery, batch, orchestration, and vector-export workflows. V2 changes
the product boundary around connections, localization, and image sizing rather than duplicating the
scientific generation pipeline.

## Quick start

### Run Studio without a permanent install

Python 3.10-3.12 and a desktop browser are required. The shortest path is:

```bash
uvx paperbanana-cn studio
```

Open <http://127.0.0.1:7860>. The interface starts in Chinese and can switch to English from
**Settings**.

### Install the command permanently

With `uv`:

```bash
uv tool install paperbanana-cn
paperbanana-cn studio
```

Or install in an isolated virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install paperbanana-cn
paperbanana-cn studio
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

The default package already includes Studio, MCP, OpenAI-compatible and Gemini adapters, and PDF
input. Optional extras are only needed for additional providers:

| Extra | Install command | Adds |
|---|---|---|
| Bedrock | `pip install "paperbanana-cn[bedrock]"` | AWS Bedrock VLM and image adapters |
| Anthropic | `pip install "paperbanana-cn[anthropic]"` | Anthropic VLM adapter |
| LiteLLM | `pip install "paperbanana-cn[litellm]"` | LiteLLM routing |
| All optional providers | `pip install "paperbanana-cn[all-providers]"` | All three extras above |

## Configure two model roles

The normal setup happens in Studio:

1. Open **Settings → VLM connection**.
2. Enter a connection name, protocol, Base URL, exact model name, timeout, and API key.
3. Choose **Save and use**.
4. Repeat under **Image connection**.
5. Return to **Methodology diagram**, select the ratio and resolution, and generate.

Browsing or editing a saved connection does not activate it. A blank key field keeps the existing
key; clearing a key is a separate confirmed action.

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/connections-zh.webp"
    width="100%"
    alt="Chinese connection manager with independent VLM profile fields"
  >
</p>

For automation, create profiles without placing keys on the command line:

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

See the
[connection guide](https://github.com/mituan-ai/PaperBanana-CN/blob/main/docs/CONNECTIONS.md)
for storage locations, supported protocols, connection tests, and explicit legacy mode.

## Generate from the CLI

Once both profiles are active:

```bash
paperbanana-cn generate \
  --input method.txt \
  --caption "Overview of the proposed architecture" \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --format png
```

Statistical plots need only the active VLM profile:

```bash
paperbanana-cn plot \
  --data results.csv \
  --intent "Compare model performance across settings" \
  --aspect-ratio 4:3 \
  --vector
```

Run `paperbanana-cn --help` for the complete command surface.

## Studio workflows

| Workflow | Connections | Output |
|---|---|---|
| **Methodology diagram** | VLM + image | Generated and refined scientific diagram |
| **Statistical plot** | VLM | Deterministically rendered plot from CSV or JSON |
| **Continue** | Depends on saved run | Additional refinement of a diagram or plot |
| **Evaluate** | VLM | Existing four-dimension quality assessment |
| **Orchestrate** | VLM + image | Planned multi-figure package from a paper |
| **Batch** | Depends on batch type | Diagram or plot batch report |
| **Sweep** | VLM + image | Ranked parameter variants |
| **Composite** | None | Deterministic multi-panel figure |
| **Runs** | None | Run, iteration, metadata, and result browser |

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-statistical-plot-en.webp"
    width="100%"
    alt="PaperBanana-CN Studio rendering a statistical line plot from CSV data"
  >
</p>

## Aspect ratio and resolution

The shared ratio set is:

`1:1` · `4:3` · `3:2` · `5:4` · `16:9` · `21:9` · `4:5` · `3:4` · `2:3` · `9:16`

Image generation uses common `1K`, `2K`, and `4K` resolution semantics. Each image adapter declares
whether it accepts native tiers, explicit pixels, fixed presets, or a prompt hint. Studio shows the
actual requested pixels or native tier. PaperBanana-CN does not silently crop, stretch, or replace
an unsupported ratio.

Statistical plots and vector exports keep their deterministic sizing path.

## MCP

PaperBanana-CN exposes 11 existing diagram, plot, evaluation, continuation, orchestration, batch,
and reference tools through one package. No separate MCP distribution is required.

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

The server reads the same active profiles as Studio and CLI. Full tool contracts are in the
[MCP guide](https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md).

## Colab, GitHub Action, and Docker

### Colab

Use the
[PaperBanana-CN Quickstart](https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb)
for a clean hosted notebook. It installs the released `paperbanana-cn` package and contains no saved
outputs or credentials.

### GitHub Action

The maintained composite action accepts separate VLM/image URLs, keys, models, ratio, and
resolution:

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

See the
[Action reference](https://github.com/mituan-ai/PaperBanana-CN/blob/main/integrations/github-action/README.md)
for every provider and output input.

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

The image runs as a non-root user and uses `paperbanana-cn` as its entry point.

## Package identity and compatibility

| Surface | V2 name |
|---|---|
| PyPI distribution | `paperbanana-cn` |
| Python import | `paperbanana_cn` |
| Command | `paperbanana-cn` |
| MCP command | `paperbanana-cn mcp` |
| MCP Registry | `io.github.mituan-ai/paperbanana-cn` |

The independent module and command names allow V2 to coexist with the upstream package in one
environment. Existing `PAPERBANANA_*` environment variables remain available only for explicit
legacy configuration.

## V1 archive

V2 is maintained on `main`. The previous implementation is frozen:

- [Browse the `v1` branch](https://github.com/mituan-ai/PaperBanana-CN/tree/v1)
- [Download the `v1.0.0` release](https://github.com/mituan-ai/PaperBanana-CN/releases/tag/v1.0.0)

V1 and V2 have independent Git histories. V1 receives no further development.

## Development and support

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest tests/ -q
```

- Ask usage questions in
  [Discussions](https://github.com/mituan-ai/PaperBanana-CN/discussions).
- Report reproducible bugs through
  [Issues](https://github.com/mituan-ai/PaperBanana-CN/issues).
- Report vulnerabilities through
  [Private Vulnerability Reporting](https://github.com/mituan-ai/PaperBanana-CN/security/advisories/new).
- Read
  [CONTRIBUTING.md](https://github.com/mituan-ai/PaperBanana-CN/blob/main/CONTRIBUTING.md)
  before opening a pull request.

Never upload API keys, private relay URLs, unpublished papers, private datasets, connection stores,
or generated run directories.

## License and upstream attribution

PaperBanana-CN is released under the
[MIT License](https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE).
Its scientific figure-generation core is based on
[`llmsresearch/paperbanana`](https://github.com/llmsresearch/paperbanana).
PaperBanana-CN is an unofficial community implementation maintained by mituan and is not affiliated
with or endorsed by the upstream authors.

## Star history

[![Star History Chart](https://api.star-history.com/svg?repos=mituan-ai/PaperBanana-CN&type=Date)](https://star-history.com/#mituan-ai/PaperBanana-CN&Date)
