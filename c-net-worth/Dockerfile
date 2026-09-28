FROM python:3.14.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl gcc libpq-dev     && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip     && pip install --no-cache-dir .     && playwright install --with-deps chromium
COPY . .
RUN useradd --create-home --uid 10001 appuser     && mkdir -p /app/logs /app/data     && chown -R appuser:appuser /app
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://127.0.0.1:8000/health || exit 1
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
