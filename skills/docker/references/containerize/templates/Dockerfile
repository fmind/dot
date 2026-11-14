# syntax=docker/dockerfile:1
# check=error=true
# Docs: https://docs.docker.com/reference/dockerfile/
# The directive above fails every build on a build-check violation (https://docs.docker.com/build/checks/);
# `docker buildx build --check .` lints without building but needs Buildx 0.15+; distro Buildx 0.13 lacks it.
FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# Use the base image Python in both stages; a managed download breaks the copied .venv.
ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 /uv /uvx /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-dev --no-editable

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Runtime images install only the locked application environment; retaining pip
# adds an unused package installer and its vendored dependency attack surface.
RUN python -m pip uninstall --yes --root-user-action=ignore pip \
  && groupadd --gid 10001 app \
  && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
# Root-owned: the runtime user can read and run the environment but never rewrite it.
COPY --from=build /app/.venv /app/.venv
USER 10001:10001
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["<slug>"]
