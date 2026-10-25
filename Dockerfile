# The live app on Render. The Playwright image has Chromium and its system
# libraries, which Lovable's JavaScript-built pricing page needs (D14).
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[live,web]" "playwright==1.64.1"

# Render sets PORT.
CMD ["sh", "-c", "uvicorn pricewatch.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
