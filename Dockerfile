# The live app on Render. The Playwright image has Chromium and its system
# libraries, which Lovable's JavaScript-built pricing page needs (D14).
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[live,web]" "playwright==1.64.1"

# The app starts a live run every 6 hours by itself, from inside the app;
# RUN_TOKEN only guards POST /run (Check now and the GitHub backup).
ENV SCHEDULE_EVERY_HOURS=6

# Render sets PORT.
CMD ["sh", "-c", "uvicorn pricewatch.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
