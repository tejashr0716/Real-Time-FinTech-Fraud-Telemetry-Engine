from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TransactionCreate(BaseModel):
    account_id: str = Field(..., json_schema_extra={"example": "b0000001-0000-0000-0000-000000000001"})
    merchant_id: str = Field(..., json_schema_extra={"example": "mer_apple_pay_direct"})
    amount: float = Field(..., gt=0, json_schema_extra={"example": 1499.00})
    currency: str = Field(default="USD", json_schema_extra={"example": "USD"})
    channel: str = Field(default="ONLINE", json_schema_extra={"example": "ONLINE"})
    ip_address: str = Field(..., json_schema_extra={"example": "198.51.100.24"})
    device_fingerprint: str = Field(..., json_schema_extra={"example": "fp_macbook_pro_m3_98f1"})
    geo_country: str = Field(default="US", json_schema_extra={"example": "US"})
    geo_city: str = Field(default="New York", json_schema_extra={"example": "New York"})
    distance_km: float = Field(default=0.0, ge=0.0)
    time_delta_seconds: float = Field(default=3600.0, ge=0.0)
    idempotency_key: str = Field(..., json_schema_extra={"example": "TX-IDEM-9928172"})

class TransactionResponse(BaseModel):
    id: str
    account_id: str
    merchant_id: str
    amount: float
    currency: str
    channel: str
    ip_address: str
    device_fingerprint: str
    geo_country: str
    geo_city: str
    fraud_score: float
    decision: str # APPROVED, FLAGGED, BLOCKED
    rules_triggered: List[str]
    eval_latency_ms: float
    idempotency_key: str
    created_at: Optional[datetime] = None
