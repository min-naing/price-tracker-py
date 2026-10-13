FROM python:3.14-slim-trixie

# Check the exact uv tag on ghcr.io/astral-sh/uv before you pin it.
# Your pyproject needs uv_build >=0.12.2,<0.13.0
COPY --from=ghcr.io/astral-sh/uv@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a /uv /uvx /bin/

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# Config uv
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Ensure installed tools can be executed out of the box
# ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Change the working directory to the `app` directory
WORKDIR /app

# Copy dependency metadata first for better layer caching.
COPY pyproject.toml uv.lock .python-version ./

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . .
RUN uv sync --locked

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Install Chromium
RUN uv run playwright install --with-deps chromium

# 2. Ensure the nonroot user owns the app directory and the installed browsers
RUN chown -R nonroot:nonroot /app /ms-playwright

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

USER nonroot

CMD ["uv", "run", "--no-sync", "price-tracker"]