import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Real-Time FinTech Fraud Telemetry Engine"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # PostgreSQL / Azure SQL Connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "fintech_fraud_db")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis In-Memory Velocity & Token Bucket Store
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "2000"))

    # RabbitMQ Event-Driven Message Broker
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    EXCHANGE_TRANSACTIONS: str = "fintech.transactions"
    QUEUE_HIGH_PRIORITY_FRAUD: str = "fraud.eval.high_priority"
    QUEUE_SETTLEMENT_AUDIT: str = "fraud.audit.settlement"
    QUEUE_DEAD_LETTER: str = "fraud.dlq"

    # Azure Cosmos DB / NoSQL Audit Store Specification
    COSMOS_ENDPOINT: str = os.getenv("COSMOS_ENDPOINT", "https://fintech-fraud-cosmos.documents.azure.com:443/")
    COSMOS_KEY: str = os.getenv("COSMOS_KEY", "mock-primary-key-for-local-audit")
    COSMOS_DATABASE: str = "FraudAuditDB"
    COSMOS_CONTAINER: str = "ThreatSignals"

    # C++ Shared Library Location
    CPP_LIB_PATH: Optional[str] = os.getenv("CPP_LIB_PATH", None)

    # Telemetry Parameters
    FRAUD_THRESHOLD_BLOCK: float = 75.0
    FRAUD_THRESHOLD_FLAG: float = 40.0

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings()
