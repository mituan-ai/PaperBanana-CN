# Contributing to PaperBanana-CN

PaperBanana-CN keeps the upstream PaperBanana scientific figure workflow and maintains three product
extensions:

1. independent VLM and image connections with custom provider, Base URL, API key, and model;
2. complete Chinese/English Studio text and errors;
3. one shared set of aspect-ratio and `1K`/`2K`/`4K` controls.

Changes outside these areas should normally be proposed to
[`llmsresearch/paperbanana`](https://github.com/llmsresearch/paperbanana) first. This keeps future
upstream synchronization reviewable and prevents a second scientific workflow from developing here.

## Before opening a pull request

Use a Discussion for design questions and an issue for a reproducible bug or scoped feature. Never
post an API key, credential-bearing URL, unpublished paper, private dataset, or unredacted run
archive.

For new relay or provider behavior, first determine whether an existing OpenAI-compatible,
Gemini-compatible, or current provider adapter already expresses the protocol. Provider code must
not branch on a relay domain, vendor name, or special model ID.

## Development setup

```bash
git clone https://github.com/mituan-ai/PaperBanana-CN.git
cd PaperBanana-CN
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows, activate with `.venv\Scripts\activate`.

## Required checks

```bash
python -m pytest tests/ -q
ruff check paperbanana_cn/ mcp_server/ tests/ scripts/
ruff format --check paperbanana_cn/ mcp_server/ tests/ scripts/
python -m build
python -m twine check dist/*
```

Provider changes require local fake-server tests for independent VLM/image URLs, authorization
headers, model names, timeouts, and redacted failures. Studio text changes require both locale
catalogs and desktop browser tests. Size changes require all ten ratios and all three resolution
tiers, including unsupported combinations that fail before a paid call.

## Pull request rules

- Keep upstream synchronization, PaperBanana-CN features, documentation, and release automation in
  separate commits.
- Add typed boundary models instead of unconstrained configuration dictionaries.
- Do not create a second provider factory, configuration precedence chain, ratio table, or pixel
  conversion path.
- Keep API keys out of fixtures, snapshots, logs, metadata, and generated archives.
- Preserve the upstream MIT license, attribution, PaperBananaBench source, and non-official status.
- Do not modify the frozen `v1` branch or archived V1 checkout.
- Explain any new production file above 500 lines or function above 60 lines.

Pull requests should state the user-visible behavior, the exact tests run, and whether the change
affects upstream synchronization.
