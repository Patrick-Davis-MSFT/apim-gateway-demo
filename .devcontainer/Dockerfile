FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm@sha256:5ff1ba19e3b9273b24ec101055172d0e75046bc9ec40780643c530d2df2c75e5

ARG UV_VERSION=0.13.6
ARG AZURE_CLI_VERSION=2.92.0
ARG SPECIFY_VERSION=1.3.2
ARG AZD_VERSION=1.37.3
ARG BICEP_VERSION=v0.49.2

ENV PIP_INDEX_URL=https://packagefeedproxy.microsoft.io/pypi/simple \
    NPM_CONFIG_REGISTRY=https://packagefeedproxy.microsoft.io/npm/ \
    YARN_NPM_REGISTRY_SERVER=https://packagefeedproxy.microsoft.io/npm/ \
    NUGET_PACKAGES=https://packagefeedproxy.microsoft.io/nuget/v3/index.json \
    UV_DEFAULT_INDEX=https://packagefeedproxy.microsoft.io/pypi/simple \
    UV_PYTHON_DOWNLOADS=never \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    UV_TOOL_DIR=/opt/tools

ARG TARGETARCH=amd64
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}" \
    && uv tool install "azure-cli==${AZURE_CLI_VERSION}" \
    && uv tool install "specify-cli==${SPECIFY_VERSION}"
ENV PATH="/root/.local/bin:${PATH}"

RUN curl --fail --location --retry 2 \
        "https://github.com/Azure/azure-dev/releases/download/azure-dev-cli_${AZD_VERSION}/azd-linux-${TARGETARCH}.tar.gz" \
        --output /tmp/azd.tar.gz \
    && tar --no-same-owner -xzf /tmp/azd.tar.gz -C /usr/local/bin \
    && mv "/usr/local/bin/azd-linux-${TARGETARCH}" /usr/local/bin/azd \
    && rm /tmp/azd.tar.gz \
    && az bicep install --version "${BICEP_VERSION}"

COPY requirements.* /opt/demo/
RUN if [ ! -f /opt/demo/requirements.lock ]; then \
        uv pip compile --generate-hashes /opt/demo/requirements.in -o /opt/demo/requirements.lock; \
    fi \
    && uv pip install --system --require-hashes -r /opt/demo/requirements.lock

COPY .devcontainer/NuGet.Config /root/.nuget/NuGet/NuGet.Config
WORKDIR /workspaces/apim-gateway-demo
