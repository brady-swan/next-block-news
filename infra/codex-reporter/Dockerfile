FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap ca-certificates nodejs npm poppler-utils \
    && rm -r /var/lib/apt/lists
WORKDIR /opt/nbn-reporter
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && npm install --global --prefix /opt/codex @openai/codex@0.154.0 \
    && python -m playwright install --with-deps chromium \
    && useradd --create-home --uid 10001 reporter
COPY . .
ENV PATH="/opt/codex/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    CODEX_HOME=/reporter-state/codex \
    NBN_REPORTER_ENABLED=false
CMD ["python", "bootstrap.py"]
