# syntax=docker/dockerfile:1
# Docs: https://docs.docker.com/reference/dockerfile/
FROM python:3.15.0rc2-slim@sha256:14684656c0069b49e897c63d52bbbe7df8a4bf189911a597403fd3b4ffeaae06 AS build
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# Use the base image Python in both stages; a managed download breaks the copied .venv.
ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.12.22@sha256:f513a91fc62fe7c17567eee97230dd198e43edb8a9fbecca843714a4358fe1bc /uv /uvx /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-dev --no-editable

FROM python:3.15.0rc2-slim@sha256:14684656c0069b49e897c63d52bbbe7df8a4bf189911a597403fd3b4ffeaae06
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Runtime images install only the locked application environment; retaining pip
# adds an unused package installer and its vendored dependency attack surface.
RUN python -m pip uninstall --yes --root-user-action=ignore pip \
  && groupadd --gid 10001 app \
  && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001:10001
COPY --from=build --chown=10001:10001 /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["<slug>"]
