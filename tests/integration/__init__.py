"""
End-to-end integration tests for QNT9 pipeline.

Tests the complete data flow:
1. Data Ingestion Service → Kafka (raw-stock-data)
2. ETL Pipeline Service → TimescaleDB → Kafka (processed-stock-data)
3. Feature Engineering Service → Redis Feature Store → Kafka (ml-features)
4. ML Training Service → MLflow
"""
