# Dockerfile
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/root/.local/bin:${PATH}" \
    APP_HOME=/app \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy app code
COPY . ${APP_HOME}

# Create user and ensure /app is owned; DO NOT touch the DB here
RUN adduser --disabled-password --gecos "" appuser \
 && mkdir -p /app/data \
 && chown -R appuser:appuser /app

USER appuser
WORKDIR ${APP_HOME}

CMD ["python3","main.py"]

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import os,socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0) if not s.connect_ex(('127.0.0.1', int(os.getenv('PORT','8080')))) else sys.exit(1)"

