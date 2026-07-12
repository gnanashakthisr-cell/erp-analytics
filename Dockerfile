FROM eclipse-temurin:17-jre AS java-base

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/java/openjdk \
    PATH=$PATH:/opt/java/openjdk/bin

WORKDIR /app

# libmagic is required by python-magic
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Java runtime directly from eclipse-temurin base image
COPY --from=java-base /opt/java/openjdk /opt/java/openjdk

COPY erp-analytics/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY erp-analytics/app/ ./app/

# Ensure temp directory exists for file uploads
RUN mkdir -p data/temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
