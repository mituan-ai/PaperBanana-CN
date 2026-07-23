# Copilot Instructions for PaperBanana-CN

## Product scope

Preserve the upstream PaperBanana scientific workflow. Repository-specific production work is
limited to independent VLM/image connections, Chinese/English Studio support, and unified aspect
ratio plus `1K`/`2K`/`4K` resolution controls.

Do not modify the frozen `v1` branch or copy V1 configuration/session code.

## Architecture

- `paperbanana_cn/core/`: upstream configuration types and workflow orchestration.
- `paperbanana_cn/providers/`: protocol adapters and provider capability declarations.
- `paperbanana_cn/connections/`: the only saved-profile, credential-reference, and runtime
  connection resolution path.
- `paperbanana_cn/studio/`: Gradio UI that consumes shared connection/configuration services.
- `paperbanana_cn/i18n/`: stable English and Chinese locale catalogs.
- `mcp_server/`: the existing FastMCP implementation launched by `paperbanana-cn mcp`.

Never add a second provider factory, configuration merge path, ratio set, size conversion table, or
translated prompt path. Core code must not recognize relay domains, channel vendors, or special
model IDs.

## Identity

- Distribution: `paperbanana-cn`
- Python package: `paperbanana_cn`
- Only command: `paperbanana-cn`
- MCP: `paperbanana-cn mcp`

Do not reintroduce `paperbanana/`, `import paperbanana`, `paperbanana`, or `paperbanana-mcp` console
scripts. Preserve `PAPERBANANA_*` environment variables for explicit legacy mode.

## Security

API keys are `SecretStr` values resolved only at the provider construction boundary. Never place a
key in repository YAML, CLI arguments, logs, exceptions, metadata, exports, screenshots, or tests.
Use fake local servers for provider tests.

## Checks

```bash
python -m pytest tests/ -q
ruff check paperbanana_cn/ mcp_server/ tests/ scripts/
ruff format --check paperbanana_cn/ mcp_server/ tests/ scripts/
```

Studio browser tests target desktop viewports only. No test may call a paid API.
