# PaperBanana-CN production image.
#
# Build:
#   docker build -t paperbanana-cn .
#
# Run the CLI:
#   docker run --rm paperbanana-cn --help
#
# Persist connection profiles and outputs:
#   docker run --rm \
#     -v paperbanana-cn-config:/home/paperbanana/.config/paperbanana-cn \
#     -v paperbanana-cn-data:/home/paperbanana/.local/share/paperbanana-cn \
#     -v "$(pwd)/outputs:/work/outputs" \
#     paperbanana-cn generate --help

FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/mituan-ai/PaperBanana-CN"
LABEL org.opencontainers.image.description="PaperBanana-CN academic figure generation workbench"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY pyproject.toml README.md LICENSE ./
COPY paperbanana_cn/ paperbanana_cn/
COPY mcp_server/ mcp_server/
COPY prompts/ prompts/
COPY data/ data/
COPY configs/ configs/

RUN pip install . \
    && cd / \
    && rm -rf /build

RUN useradd --create-home --uid 1000 paperbanana \
    && mkdir -p \
        /home/paperbanana/.config/paperbanana-cn \
        /home/paperbanana/.local/share/paperbanana-cn \
        /work/outputs \
    && chown -R paperbanana:paperbanana /home/paperbanana /work

USER paperbanana
WORKDIR /work

ENTRYPOINT ["paperbanana-cn"]
CMD ["--help"]
