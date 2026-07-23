## User-visible change

<!-- What problem is solved and what behavior changes? -->

## Scope

- [ ] Independent VLM/image connections
- [ ] Chinese/English Studio
- [ ] Aspect ratio or resolution
- [ ] Packaging, MCP, Action, Docker, or documentation
- [ ] Upstream synchronization (kept in a separate commit)

## Verification

<!-- List exact commands and fake-provider/browser scenarios exercised. -->

- [ ] `python -m pytest tests/ -q`
- [ ] `ruff check paperbanana_cn/ mcp_server/ tests/ scripts/`
- [ ] `ruff format --check paperbanana_cn/ mcp_server/ tests/ scripts/`
- [ ] No paid API was called
- [ ] No API key, private URL, paper, dataset, output, or local state is included
- [ ] No duplicate provider/configuration/size/i18n implementation was introduced
