# PaperBanana-CN GitHub Action

Generate a methodology figure from a LaTeX section with independent VLM and image-generation
connections. The action stores both credentials in an isolated temporary XDG directory, passes only
saved connection profiles to the CLI, and removes the directory with the GitHub runner.

## Quick start

```yaml
name: Generate methodology figure

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  figure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: mituan-ai/PaperBanana-CN/integrations/github-action@main
        with:
          tex-file: sections/method.tex
          caption: "Overview of our proposed framework"

          vlm-provider: openai
          vlm-base-url: ${{ vars.VLM_BASE_URL }}
          vlm-model: ${{ vars.VLM_MODEL }}
          vlm-api-key: ${{ secrets.VLM_API_KEY }}

          image-provider: openai_imagen
          image-base-url: ${{ vars.IMAGE_BASE_URL }}
          image-model: ${{ vars.IMAGE_MODEL }}
          image-api-key: ${{ secrets.IMAGE_API_KEY }}
          image-size-mode: explicit_pixels

          aspect-ratio: "16:9"
          resolution: "2K"
          budget: "0.50"
```

Use repository variables for non-secret URLs and model names, and GitHub Actions secrets for API
keys. The VLM and image connections can point to one relay or two completely different services.
The action never places a key on a command line.

## Inputs

| Input | Default | Description |
|---|---|---|
| `tex-file` | required | LaTeX source containing the methodology section |
| `caption` | required | Figure caption or communicative intent |
| `section` | `Method` | Section-title substring to extract |
| `output-path` | `figures/method_overview.png` | Generated PNG or JPEG path |
| `snippet-path` | image path with `.tex` | Generated LaTeX snippet |
| `figure-label` | `fig:method-overview` | LaTeX label |
| `figure-width` | `\columnwidth` | `\includegraphics` width |
| `vlm-provider` | `openai` | VLM provider adapter |
| `vlm-base-url` | provider default | Independent VLM Base URL |
| `vlm-model` | required | Exact VLM model identifier |
| `vlm-api-key` | required | VLM API key from a secret |
| `image-provider` | `openai_imagen` | Image provider adapter |
| `image-base-url` | provider default | Independent image Base URL |
| `image-model` | required | Exact image model identifier |
| `image-api-key` | required | Image API key from a secret |
| `image-size-mode` | `fixed` | `fixed`, `explicit_pixels`, `native_tier`, or `prompt_hint` |
| `aspect-ratio` | `3:2` | One of the ten supported ratios |
| `resolution` | `1K` | `1K`, `2K`, or `4K` |
| `iterations` | `3` | Visualizer/Critic refinement rounds |
| `optimize` | `false` | Enable input optimization |
| `budget` | empty | Optional USD budget cap |
| `seed` | empty | Optional random seed |
| `paperbanana-version` | `2.0.1` | Exact PyPI release to install |
| `commit` | `true` | Commit and push generated files |
| `commit-message` | PaperBanana-CN update | Commit message |

The selected provider must support the requested ratio and resolution. Unsupported combinations
fail before generation instead of being silently resized or cropped.

## Outputs

| Output | Description |
|---|---|
| `image-path` | Repository-relative generated image path |
| `snippet-path` | Repository-relative LaTeX snippet path |

The action uses `paperbanana-cn==2.0.1`, creates two saved profiles with
`connections add --api-key-env`, and runs `paperbanana-cn generate` in profile mode. It does not use
the legacy provider environment-variable merge path.
