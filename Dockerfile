# ─── Retail Insight — Hugging Face Spaces (Docker SDK) ────────────────────────
# Runs the FastAPI backend on localhost:8000 and Streamlit on port 7860
# (HF Spaces' public port). Both processes live in one container; the
# Streamlit app talks to FastAPI over localhost.
#
# Build:    docker build -t retail-insight .
# Run:      docker run -p 7860:7860 retail-insight
# Browse:   http://localhost:7860/
#
# Deploy to HF Spaces:
#   1. Create a new Space, SDK = Docker, hardware = CPU basic (free).
#   2. Push this repo as the Space's git remote.
#   3. Done — no Space secrets required (BYO-key UX handles AI features).
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Suppress interactive apt prompts, ensure UTF-8 logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# HF Spaces requires a writable HOME and runs as a non-root user.
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Minimal system libs — pyarrow needs libstdc++, plotly is pure-python.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create the unprivileged user HF Spaces expects.
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

# Install Python deps first (cache layer)
COPY --chown=user requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy the app
COPY --chown=user . .

# Expose Streamlit's port — FastAPI stays internal on 8000
EXPOSE 7860

# Healthcheck — HF Spaces will mark the Space healthy once Streamlit responds
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -fsS http://localhost:7860/_stcore/health || exit 1

CMD ["bash", "start.sh"]
