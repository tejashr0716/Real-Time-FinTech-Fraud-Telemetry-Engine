from pydantic import BaseModel
from typing import List, Optional

class TelemetryStreamSnapshot(BaseModel):
    timestamp_ms: int
    tps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_evaluated: int
    blocked_count: int
    flagged_count: int
    approved_count: int
    fraud_block_rate_pct: float
    active_ws_clients: int

class ThreatAlert(BaseModel):
    event_type: str = "THREAT_BLOCKED"
    transaction_id: str
    account_id: str
    merchant_name: str
    amount: float
    fraud_score: float
    primary_rule: str
    geo_city: str
    geo_country: str
    timestamp_ms: int
