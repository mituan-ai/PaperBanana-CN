# PaperBanana — publication-quality academic diagrams from text descriptions.
#
# Build:
#   docker build -t paperbanana .
#
# Run (Gemini, free tier — get a key at https://aistudio.google.com/app/apikey):
#   docker run --rm -e GOOGLE_API_KEY paperbanana generate --help
#
# Generate a diagram, persisting outputs to the host:
#   docker run --rm -e GOOGLE_API_KEY \
#     -v "$(pwd)/method.txt:/work/method.txt:ro" \
#     -v "$(pwd)/outputs:/work/outputs" \
#     paperbanana generate --input method.txt --caption "Overview of our framework"

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Everything the hatchling wheel build needs:
#  - pyproject.toml (build config), README.md (project.readme), LICENSE (SPDX license file)
#  - paperbanana_cn/ and mcp_server/ (wheel packages)
#  - prompts/, data/, configs/ (force-included package data, resolved at runtime
#    relative to the installed package)
COPY pyproject.toml README.md LICENSE ./
COPY paperbanana_cn/ paperbanana_cn/
COPY mcp_server/ mcp_server/
COPY prompts/ prompts/
COPY data/ data/
COPY configs/ configs/

# Install the package (the wheel embeds prompts/, data/, configs/), then drop
# the build context — it is fully duplicated inside site-packages.
RUN pip install ".[google,openai,pdf]" && cd / && rm -rf /build

# Non-root runtime user; /work is the writable working directory where the CLI
# reads inputs and writes the outputs/ folder (mount volumes here).
RUN useradd --create-home --uid 1000 paperbanana \
    && mkdir /work \
    && chown paperbanana:paperbanana /work

USER paperbanana
WORKDIR /work

ENTRYPOINT ["paperbanana"]
CMD ["--help"]
