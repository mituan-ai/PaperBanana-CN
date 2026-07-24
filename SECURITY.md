# Security Policy

## Supported versions

| Version | Status |
|---|---|
| `2.x` | Supported |
| `1.x` / `v1` branch | Frozen and unsupported |

Security fixes are made on `main` and released in the latest V2 package. The frozen V1 branch is
kept for archival and migration purposes only.

## Report a vulnerability

Do not disclose a vulnerability in a public issue or Discussion. Use
[GitHub Private Vulnerability Reporting](https://github.com/mituan-ai/PaperBanana-CN/security/advisories/new)
so the report and follow-up remain private.

Include:

- affected version or commit;
- impact and realistic attack path;
- minimal reproduction steps;
- logs with every API key, URL credential, paper, and private dataset removed;
- a proposed mitigation, when available.

## Security boundaries

### API credentials

Saved connection profiles contain only credential references. API keys are stored outside the
repository in the platform-specific PaperBanana-CN data directory with private file permissions.
Keys must never appear in YAML, command-line arguments, logs, run metadata, exported packages,
screenshots, or issue reports.

The GitHub Action accepts keys through GitHub Secrets and forwards only environment-variable names
to `connections add --api-key-env`.

### External model services

Method text, images, prompts, and generated artifacts may be sent to the VLM or image service
selected by the user. PaperBanana-CN cannot provide privacy guarantees for third-party or relay
services. Review their retention, training, and regional-processing policies before submitting
confidential research.

### Generated plotting code

The statistical plotting workflow generates and executes Python plotting code. Treat generated code
and untrusted input data as untrusted, inspect them before reuse, and run sensitive workloads in an
isolated environment.

### MCP

`paperbanana-cn mcp` uses local stdio transport. MCP clients can ask it to read input paths and write
outputs with the permissions of the current user. Configure only trusted clients and do not expose
the process through an unauthenticated remote bridge.

### Artifacts and datasets

Before sharing a run, inspect images, prompts, logs, metadata, PDFs, and manifests for private paper
content or local paths. PaperBananaBench remains an upstream reference dataset with its own source
and usage considerations.
