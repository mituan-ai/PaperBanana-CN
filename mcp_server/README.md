# PaperBanana MCP Server

MCP server that exposes PaperBanana's diagram and plot generation as tools for Claude Code, Cursor, or any MCP-compatible client.

## Tools

| Tool | Description |
|------|-------------|
| `generate_diagram` | Generate a methodology diagram from text context + caption |
| `continue_run` | Continue refinement for an existing `run_*` directory (optional critic feedback) |
| `generate_plot` | Generate a statistical plot from JSON data + intent description |
| `continue_diagram` | Continue a prior methodology `run_*` (more refinement and/or critic feedback); returns JSON paths |
| `continue_plot` | Continue a prior statistical-plot `run_*`; same JSON contract as `continue_diagram` |
| `evaluate_diagram` | Compare a generated diagram against a human reference (4 dimensions) |
| `evaluate_plot` | Compare a generated statistical plot against a human reference (4 dimensions) |
| `download_references` | Download the expanded reference set for stronger retrieval |
| `orchestrate_figures` | Plan / generate a full-paper figure package (same workflow as `paperbanana-cn orchestrate`); returns JSON paths and status |
| `batch_diagrams` | Run a methodology batch from a manifest path (`paperbanana-cn batch`) |
| `batch_plots` | Run a statistical plot batch from a manifest path (`paperbanana-cn plot-batch`) |

### Batch and orchestration tools

These tools return **pretty-printed JSON** with absolute paths to `batch_report.json`, `figure_package.json`, `orchestration_plan.json`, `figures.tex`, `captions.md`, and per-item summaries. Use `dry_run=True` on `orchestrate_figures` to plan only (no generation API calls).

Long runs execute in a **worker thread** so they do not block the MCP server event loop; progress lines are logged via structlog (`mcp_orchestrate`, `mcp_batch_diagrams`, `mcp_batch_plots`).

On validation errors (missing manifest, bad flags), the JSON body includes `"error"` and `"strict_success": false`.

### Continue tools

`continue_diagram` and `continue_plot` mirror ``paperbanana-cn generate --continue-run`` / Studio continue: they load `run_input.json` and the latest iteration under `output_dir` / `run_id`, then run more visualizer–critic rounds. Pick the tool that matches the run’s `diagram_type` (`methodology` vs `statistical_plot`); otherwise the response is `strict_success: false` with a hint to use the other tool. Successful responses include `final_image_path`, `run_dir`, and `metadata_path` when present.

## Installation

Install PaperBanana-CN, then create and activate the VLM and image profiles used by the server:

```bash
pip install paperbanana-cn
paperbanana-cn connections list
```

### Claude Code

Add to `.claude/claude_code_config.json` (or project-level):

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

### Cursor

Add to `.cursor/mcp.json` in your project:

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

For an activated environment where PaperBanana-CN is already installed, the equivalent command is:

```json
{
  "mcpServers": {
    "paperbanana-cn": {
      "command": "paperbanana-cn",
      "args": ["mcp"]
    }
  }
}
```

## Skills (Claude Code)

This repo ships with 3 Claude Code skills in `.claude/skills/`:

| Skill | Description |
|-------|-------------|
| `/generate-diagram <file> [caption]` | Generate a methodology diagram from a text file |
| `/generate-plot <data-file> [intent]` | Generate a statistical plot from CSV or JSON data |
| `/evaluate-diagram <generated> <reference>` | Evaluate a diagram against a human reference |

Skills are available automatically when you clone the repo and use Claude Code.

## Usage Examples

### Generate a methodology diagram

```
User: Generate a diagram for this methodology:
      "Our framework uses a two-phase pipeline: first a linear planning
       phase with Retriever, Planner, and Stylist agents, followed by
       an iterative refinement phase with Visualizer and Critic agents."
      Caption: "Overview of the PaperBanana multi-agent framework"
```

### Continue a previous run

```
User: Continue run run_20260218_125448_e7b876 with feedback: "Use larger font for axis labels"
```

The tool resolves `outputs/<run_id>/` using the same output directory as other MCP tools (from `Settings`, typically `outputs`). The run must contain `run_input.json` from a prior `generate_diagram` or `generate_plot` call (or CLI).

### Generate a statistical plot

```
User: Create a bar chart from this data:
      {"models": ["GPT-4", "Claude", "Gemini"], "accuracy": [0.92, 0.94, 0.91]}
      Intent: "Bar chart comparing model accuracy on benchmark"
```

### Evaluate a diagram

```
User: Evaluate the diagram at ./output.png against the reference at ./reference.png
      Context: [methodology text]
      Caption: "System architecture overview"
```

## Configuration

MCP tools use the same saved profiles as Studio and CLI. Each tool accepts `vlm_connection` and,
when image generation is required, `image_connection`; otherwise the active profile for that role is
used. The two roles may use different providers, URLs, API keys, models, and timeouts.

Environment variables and YAML provider fields are legacy inputs. They are used only when the tool
call sets `legacy_connections=true`, and legacy provider arguments cannot be mixed with profile IDs.
See [Connection configuration](../docs/CONNECTIONS.md) for storage and migration details.
