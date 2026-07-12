FROM eclipse-temurin:17-jre AS java-base

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/java/openjdk \
    PATH=$PATH:/opt/java/openjdk/bin

WORKDIR /app

# Copy Java runtime directly from eclipse-temurin base image (avoids network-based apt-get issues on Render)
COPY --from=java-base /opt/java/openjdk /opt/java/openjdk

COPY erp-analytics/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY erp-analytics/app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
