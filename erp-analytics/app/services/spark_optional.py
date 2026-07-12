import os
import sys
import logging

logger = logging.getLogger(__name__)

def maybe_use_spark(file_size_mb: float) -> bool:
    from app.config import settings
    return file_size_mb > settings.USE_SPARK_ABOVE_MB

def run_with_spark(df, ops):
    """
    Lazy escape hatch for large files.
    """
    from pyspark.sql import SparkSession

    if os.name == "nt" and "PYSPARK_PYTHON" not in os.environ:
        python_path = sys.executable
        os.environ["PYSPARK_PYTHON"] = python_path
        os.environ.setdefault("PYSPARK_DRIVER_PYTHON", python_path)

    spark = SparkSession.builder.master("local[*]").appName("ERP-Analytics-Optional").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    try:
        pass # Placeholder for spark logic if ever needed
    finally:
        spark.stop()
