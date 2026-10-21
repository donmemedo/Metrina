# syntax=docker/dockerfile:1
# Tag pins only: this build host could not reach a registry to resolve digests. In CI, pin by digest (Renovate/Dependabot docker ecosystem).
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.lock .
RUN --mount=type=cache,target=/root/.cache/pip pip install --timeout 60 --retries 10 -r requirements.lock
COPY app.py .
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
# One process on purpose: the stores are in memory (see docs/architecture.md). No proxy-header magic: app.py parses X-Forwarded-For itself, only when TRUST_PROXY=1.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-server-header", "--timeout-keep-alive", "5", "--limit-concurrency", "200"]
