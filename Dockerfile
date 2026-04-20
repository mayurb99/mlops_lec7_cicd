# ════════════════════════════════════════════════════════
# Dockerfile — Churn Prediction API
# Lecture 6 — Docker & DockerHub
# ════════════════════════════════════════════════════════
#
# Build:  docker build -t churn-api:v1 .
# Run:    docker run -p 8000:8000 churn-api:v1
# Test:   curl http://localhost:8000/health
# ════════════════════════════════════════════════════════

# ── Stage 1: Base image ───────────────────────────────────
# python:3.11-slim = 200MB vs python:3.11 = 1GB
# Always use -slim for production ML APIs
FROM python:3.11-slim

# ── Set working directory ─────────────────────────────────
# All subsequent commands run from /app inside the container
WORKDIR /app

# ── Install system dependencies ───────────────────────────
# curl needed for health checks; --no-install-recommends keeps it small
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── LAYER CACHING TRICK ───────────────────────────────────
# Copy requirements.txt BEFORE copying application code.
# If requirements.txt hasn't changed, Docker reuses the cached
# pip install layer — saves 2-5 minutes on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ─────────────────────────────────
# This comes AFTER pip install so code changes don't
# trigger a full dependency reinstall
COPY app.py .
COPY models/ ./models/

# ── Environment variables ─────────────────────────────────
# Configure paths and settings via environment variables
# Override at runtime: docker run -e MODEL_PATH=/other/path churn-api:v1
ENV MODEL_PATH=/app/models/churn_model.pkl
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# ── Document the port ─────────────────────────────────────
# EXPOSE documents which port the container uses.
# It does NOT open the port — the -p flag does that at docker run.
EXPOSE 8000

# ── Startup command ───────────────────────────────────────
# CMD is the default command run when container starts.
# --host 0.0.0.0 is REQUIRED — without it, the API is only
# accessible inside the container (localhost), not from outside.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
