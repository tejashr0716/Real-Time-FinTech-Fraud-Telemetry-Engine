import pytest
from spark.fraud_batch_analytics import run_spark_analytics

def test_spark_analytics_execution():
    # Verify Spark runs without unhandled exceptions
    run_spark_analytics()
