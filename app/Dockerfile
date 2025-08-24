# Dockerfile (uv + single venv at /opt/venv)
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=0 \
    PATH="/opt/venv/bin:/root/.local/bin:${PATH}" \
    APP_HOME=/app \
    SQLITE_DB_PATH=data.db \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates build-essential gcc \
    && rm -rf /var/lib/apt/lists/*


WORKDIR ${APP_HOME}

# Lockfile-first for caching
COPY ./requirements.txt ./requirements.txt


RUN pip install -r requirements.txt

# Copy app code
COPY . ${APP_HOME}

# Non-root + SQLite dir
RUN adduser --disabled-password --gecos "" appuser \
 && chown -R appuser:appuser ${APP_HOME}

USER appuser
WORKDIR ${APP_HOME}

# Use module name, not filename
CMD ["python3","main.py"]

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import os,socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0) if not s.connect_ex(('127.0.0.1', int(os.getenv('PORT','8080')))) else sys.exit(1)"

