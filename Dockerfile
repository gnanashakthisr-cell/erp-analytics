FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH=$PATH:/usr/lib/jvm/java-17-openjdk-amd64/bin

WORKDIR /app

# Install Java 17 headless (required for PySpark)
RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY erp-analytics/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY erp-analytics/app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
