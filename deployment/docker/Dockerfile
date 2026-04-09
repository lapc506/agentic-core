# Stage 1: Flutter Web build
FROM ghcr.io/cirruslabs/flutter:stable AS flutter-build
WORKDIR /app
COPY ui/pubspec.* ./
RUN flutter pub get
COPY ui/ .
RUN flutter build web --release

# Stage 2: Python build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY proto/ proto/
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Stage 3: Production image
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src /app/src
COPY --from=flutter-build /app/build/web /app/web

WORKDIR /app
ENV PYTHONPATH=/app/src:/usr/local/lib/python3.12/site-packages
ENV AGENTIC_MODE=standalone
ENV AGENTIC_STATIC_DIR=/app/web
ENV AGENTIC_WS_PORT=8765
ENV AGENTIC_GRPC_PORT=50051

EXPOSE 8765 50051 9090
USER nonroot:nonroot
ENTRYPOINT ["python", "-m", "agentic_core.runtime"]
