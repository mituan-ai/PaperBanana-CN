<!-- mcp-name: io.github.mituan-ai/paperbanana-cn -->

<p align="right">
  <strong>English</strong> ·
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/README_CN.md">简体中文</a>
</p>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/hero.webp"
    width="100%"
    alt="PaperBanana-CN scientific figure workbench with a real multimodal fault-diagnosis figure"
  >
</p>

<p align="center">
  <a href="#start-in-60-seconds"><img src="https://img.shields.io/badge/LAUNCH_STUDIO-uvx_paperbanana--cn_studio-147862?style=for-the-badge&logo=gnometerminal&logoColor=white" alt="Launch Studio"></a>
  <a href="https://pypi.org/project/paperbanana-cn/"><img src="https://img.shields.io/badge/INSTALL-PYPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white" alt="Install from PyPI"></a>
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md"><img src="https://img.shields.io/badge/CONNECT-11_MCP_TOOLS-52605B?style=for-the-badge" alt="Connect through MCP"></a>
  <a href="https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb"><img src="https://img.shields.io/badge/TRY-COLAB-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white" alt="Try in Colab"></a>
</p>

<p align="center">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mituan-ai/PaperBanana-CN/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=CI" alt="CI status"></a>
  <img src="https://img.shields.io/badge/Package-2.0.1-147862?style=flat-square" alt="Package version 2.0.1">
  <img src="https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 to 3.12">
  <img src="https://img.shields.io/badge/Gradio-6.20.0-F97316?style=flat-square&logo=gradio&logoColor=white" alt="Gradio 6.20.0">
  <a href="https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-52605B?style=flat-square" alt="MIT License"></a>
</p>

<p align="center">
  <strong>Turn method descriptions and research data into scientific diagrams and statistical plots.</strong><br>
  Keep the PaperBanana workflow; choose your own VLM, image service, interface language, aspect ratio, and resolution.
</p>

## See it work

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-workflow.gif"
    width="960"
    alt="PaperBanana-CN Studio progressing from configured inputs through generation to a completed scientific figure"
  >
</p>

<p align="center">
  <sub>One real Studio run: configured input → live pipeline stages → completed result. No credentials or private endpoints are shown.</sub>
</p>

## Real outputs, not mockups

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/showcase.webp"
    width="100%"
    alt="A PaperBanana-CN showcase containing a methodology diagram, a refined concept figure, and a statistical plot"
  >
</p>

The methodology diagrams were generated and refined through the configured VLM and image roles.
The statistical plot uses PaperBanana's deterministic plotting path; its values are synthetic
demonstration data.

## What V2 actually adds

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/capabilities.svg"
    width="100%"
    alt="PaperBanana-CN V2 adds independent model connections, a bilingual Studio, and exact output sizing"
  >
</p>

| Independent model rails | A complete bilingual Studio | Exact output control |
|---|---|---|
| Give the VLM and image generator different protocols, Base URLs, API keys, model names, and timeouts. | Switch the interface between Chinese and English without rewriting prompts, paper text, or labels inside the figure. | Choose 10 aspect ratios and `1K` / `2K` / `4K`; unsupported combinations fail before a paid image request. |

Studio, CLI, and MCP resolve the same saved connections. API keys remain outside the repository,
are never filled back into the browser, and are excluded from run metadata.

## Start in 60 seconds

### 1. Launch the desktop Studio

You need Python 3.10-3.12, [uv](https://docs.astral.sh/uv/), and a desktop browser:

```bash
uvx paperbanana-cn studio
```

Open <http://127.0.0.1:7860>. `uvx` uses an isolated environment and does not modify Debian or
Ubuntu's system Python.

### 2. Connect the two model roles

Open **Settings → VLM connection**, enter the protocol, Base URL, API key, exact model name, and
timeout, then select **Save and use**. Repeat under **Image connection**.

> [!TIP]
> The two roles may use the same relay or completely different services. Editing a saved
> connection does not activate it, and leaving the key field blank preserves the existing key.

<details>
<summary><strong>Show the connection manager</strong></summary>

<br>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/connections-zh.webp"
    width="100%"
    alt="PaperBanana-CN connection manager with independent VLM service fields"
  >
</p>

Supported protocols, credential storage, connection tests, and explicit legacy mode are documented
in the [connection guide](https://github.com/mituan-ai/PaperBanana-CN/blob/main/docs/CONNECTIONS.md).

</details>

### 3. Generate

Choose **Methodology diagram**, add the method content and communicative intent, select the aspect
ratio and resolution, and run. The result canvas keeps the final figure, real output size,
iteration history, and download actions together.

The same task from the CLI:

```bash
paperbanana-cn generate \
  --input method.txt \
  --caption "Overview of the proposed architecture" \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --format png
```

## A workbench built around the result

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/studio-tour.webp"
    width="100%"
    alt="Annotated PaperBanana-CN Studio showing task inputs, size controls, and the result canvas"
  >
</p>

| Area | Workflows | Required connections |
|---|---|---|
| **Create** | Methodology diagram, statistical plot | VLM + image / VLM only |
| **Improve** | Continue a saved run, quality evaluation | Determined by the run / VLM only |
| **Automate** | Full-paper orchestration, batch, parameter sweep | Determined by the task |
| **Tools** | Multi-panel composite, run browser | None |

Task inputs stay in the left work area. The result canvas is the visual center; completed logs
collapse out of the way, while failed runs keep the input and expose the actionable error.

## One scientific workflow

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/workflow.svg"
    width="100%"
    alt="Independent VLM and image connections feeding the existing scientific figure pipeline"
  >
</p>

PaperBanana-CN does not maintain a second scientific pipeline. Retrieval, planning, candidate
generation, critique, refinement, deterministic plotting, recovery, batch processing,
orchestration, and vector export continue through the upstream PaperBanana workflow.

## Use it your way

| Entry point | Best for | Start here |
|---|---|---|
| **Studio** | Interactive figure production and connection management | `paperbanana-cn studio` |
| **CLI** | Reproducible local runs and scripts | `paperbanana-cn generate --help` |
| **MCP** | Calling 11 figure tools from an MCP client | `paperbanana-cn mcp` |
| **GitHub Action** | Generating figures inside a repository workflow | [Action reference](https://github.com/mituan-ai/PaperBanana-CN/blob/main/integrations/github-action/README.md) |
| **Docker** | A pinned, isolated runtime | `ghcr.io/mituan-ai/paperbanana-cn:2.0.1` |
| **Colab** | Trying the package in a hosted notebook | [Quickstart notebook](https://colab.research.google.com/github/mituan-ai/PaperBanana-CN/blob/main/notebooks/PaperBanana_CN_Quickstart.ipynb) |

<details>
<summary><strong>MCP client configuration</strong></summary>

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

The server reads the same active connections as Studio and CLI. See the
[MCP guide](https://github.com/mituan-ai/PaperBanana-CN/blob/main/mcp_server/README.md) for all
11 tools and their arguments.

</details>

<details>
<summary><strong>Docker launch</strong></summary>

```bash
docker run --rm -p 7860:7860 \
  -v paperbanana-cn-config:/home/paperbanana/.config/paperbanana-cn \
  -v paperbanana-cn-data:/home/paperbanana/.local/share/paperbanana-cn \
  -v paperbanana-cn-outputs:/work/outputs \
  ghcr.io/mituan-ai/paperbanana-cn:2.0.1 \
  studio --host 0.0.0.0
```

</details>

## Output control without surprises

**Aspect ratios**

`1:1` · `4:3` · `3:2` · `5:4` · `16:9` · `21:9` · `4:5` · `3:4` · `2:3` · `9:16`

**Resolution tiers**

`1K` · `2K` · `4K`

Each image adapter declares whether it accepts native tiers, explicit pixels, fixed presets, or a
prompt hint. Studio shows the actual request size or native tier. It never silently crops,
stretches, or substitutes an unsupported ratio.

<details>
<summary><strong>Permanent install, source setup, and optional providers</strong></summary>

Install the command in an isolated, uv-managed environment:

```bash
uv tool install paperbanana-cn
paperbanana-cn studio
```

Run the current source checkout:

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv sync
uv run paperbanana-cn studio
```

The default package includes Studio, MCP, PDF input, OpenAI-compatible services, and Gemini.

| Optional adapter | Install |
|---|---|
| AWS Bedrock | `uv tool install "paperbanana-cn[bedrock]"` |
| Anthropic | `uv tool install "paperbanana-cn[anthropic]"` |
| LiteLLM | `uv tool install "paperbanana-cn[litellm]"` |
| All optional providers | `uv tool install "paperbanana-cn[all-providers]"` |

For CI, read credentials from environment variables rather than command-line values:

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

## V1 is preserved. V2 moves forward.

<p align="center">
  <img
    src="https://raw.githubusercontent.com/mituan-ai/PaperBanana-CN/main/assets/readme/lineage.svg"
    width="100%"
    alt="PaperBanana-CN V1 is frozen while V2 is maintained on main"
  >
</p>

V2 is maintained on `main` as the `paperbanana-cn` distribution, `paperbanana_cn` Python module,
and `paperbanana-cn` command. V1 remains available as a frozen historical release:

- [Browse the independent `v1` branch](https://github.com/mituan-ai/PaperBanana-CN/tree/v1)
- [Download the `v1.0.0` release](https://github.com/mituan-ai/PaperBanana-CN/releases/tag/v1.0.0)

## Project and community

PaperBanana-CN is maintained by [mituan](https://github.com/mituan-ai).

- Ask usage questions in [Discussions](https://github.com/mituan-ai/PaperBanana-CN/discussions).
- Report reproducible bugs in [Issues](https://github.com/mituan-ai/PaperBanana-CN/issues).
- Report vulnerabilities through [Private Vulnerability Reporting](https://github.com/mituan-ai/PaperBanana-CN/security/advisories/new).
- Read [CONTRIBUTING.md](https://github.com/mituan-ai/PaperBanana-CN/blob/main/CONTRIBUTING.md) before opening a pull request.

PaperBanana-CN is released under the
[MIT License](https://github.com/mituan-ai/PaperBanana-CN/blob/main/LICENSE). Its scientific
figure-generation core is based on
[`llmsresearch/paperbanana`](https://github.com/llmsresearch/paperbanana).
This is an unofficial community implementation and is not affiliated with or endorsed by the
upstream authors.

<details>
<summary><strong>Development checks</strong></summary>

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check paperbanana_cn/ mcp_server/ tests/ scripts/
```

Never upload API keys, private relay URLs, unpublished papers, private datasets, local connection
stores, or generated run directories.

</details>

## Star history

<a href="https://www.star-history.com/?repos=mituan-ai%2FPaperBanana-CN&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&theme=dark&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=mituan-ai/PaperBanana-CN&type=date&legend=top-left&sealed_token=tONDl7QT6gBodlxbICyg-BGsu060cE2rb7tZmOubJS6r7ZQMt8tGi9pUE274ujDrVgxHmy3U6QwUFtqtCDbU5abOpd8t9gKCK6B48Typy5z9FLLBvnF4uA" />
 </picture>
</a>
