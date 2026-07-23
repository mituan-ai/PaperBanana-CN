# Connection configuration

PaperBanana-CN resolves the vision-language model (VLM) and image generator as two independent
connections. A connection profile contains one role, provider adapter, Base URL, model, timeout,
optional image size mode, and a reference to a separately stored credential.

## Default profile mode

Studio, CLI generation commands, and MCP tools use profile mode by default. Resolution order is:

1. A profile ID supplied for the current call.
2. The active saved profile for that role.
3. A clear configuration error when no valid profile exists.

Environment variables and YAML provider fields do not override saved profiles. Use
`paperbanana-cn connections list` to inspect active profiles without exposing credentials.

Create one profile for each role:

```bash
paperbanana-cn connections add \
  --role vlm --name "VLM relay" --provider openai \
  --base-url https://vlm.example.com/v1 --model vlm-model

paperbanana-cn connections add \
  --role image --name "Image relay" --provider openai_imagen \
  --base-url https://image.example.com/v1 --model image-model \
  --size-mode explicit_pixels
```

Both commands prompt for the API key. The VLM and image profiles may point to the same service or to
completely different endpoints. Provider names select existing adapters; they are not relay brands.

Manage profiles with:

```bash
paperbanana-cn connections list
paperbanana-cn connections edit <profile-id> --name "New name"
paperbanana-cn connections use --role vlm <profile-id>
paperbanana-cn connections test <profile-id>
paperbanana-cn connections delete <profile-id>
```

Image tests perform local configuration and capability validation unless `--paid` is supplied. A
paid test sends a minimal image request. VLM tests send a small visual request that asks for JSON.

## Storage and secrets

Paths are selected with `platformdirs`. On Linux the defaults are:

- Non-secret profiles: `~/.config/paperbanana-cn/connections.json`
- API keys: `~/.local/share/paperbanana-cn/secrets.json`

Both files are written atomically with private permissions. The profile document stores only a
credential reference. API keys are excluded from `show-config`, logs, run metadata, benchmark
reports, and exported settings snapshots. A missing credential, corrupt file, or concurrent revision
conflict is reported instead of silently resetting configuration.

## Image size modes

Image providers declare their supported ratios, resolutions, and request format. The optional image
profile size mode is mainly for OpenAI-compatible endpoints whose wire behavior differs:

- `fixed`: the endpoint accepts only its declared native presets.
- `explicit_pixels`: the endpoint accepts exact `WIDTHxHEIGHT` strings.
- `native_tier`: the endpoint accepts an aspect ratio plus `1K`, `2K`, or `4K` tier.
- `prompt_hint`: the adapter can request the ratio only through the prompt.

Do not select `explicit_pixels` unless the endpoint documents that behavior. Unsupported ratio and
resolution combinations fail before a paid generation call; PaperBanana-CN does not silently crop,
stretch, or substitute a nearby ratio.

## Explicit legacy mode

Legacy mode preserves the upstream `.env`, environment variable, YAML, and provider option behavior:

```bash
paperbanana-cn generate \
  --legacy-connections \
  --vlm-provider openai --vlm-model gpt-5.2 \
  --image-provider openai_imagen --image-model gpt-image-1.5 \
  --input method.txt --caption "Overview of the method"
```

Profile IDs cannot be combined with `--legacy-connections`. Existing upstream settings can be
imported once with `paperbanana-cn connections import-legacy`; PaperBanana-CN never scans or imports
an old repository automatically.
