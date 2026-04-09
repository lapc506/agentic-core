# Dockerfile for agentic-core standalone mode
#
# Pre-build Flutter Web BEFORE running docker build:
#   make build-web    (or: cd ui && flutter build web --release)
#
# The built files at ui/build/web/ are copied into the image.
# No Flutter SDK needed inside Docker — keeps the image ~150MB.

# Stage 1: Python build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY proto/ proto/
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Stage 2: Production image
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src /app/src
COPY ui/build/web /app/web

WORKDIR /app
ENV PYTHONPATH=/app/src:/usr/local/lib/python3.12/site-packages
ENV AGENTIC_MODE=standalone
ENV AGENTIC_STATIC_DIR=/app/web
ENV AGENTIC_WS_PORT=8765
ENV AGENTIC_GRPC_PORT=50051

EXPOSE 8765 50051 9090
USER nonroot:nonroot
ENTRYPOINT ["python", "-m", "agentic_core.runtime"]
