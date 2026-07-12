FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# libmagic is required by python-magic
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*



COPY erp-analytics/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY erp-analytics/app/ ./app/

# Ensure temp directory exists for file uploads
RUN mkdir -p data/temp

EXPOSE 8000

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
