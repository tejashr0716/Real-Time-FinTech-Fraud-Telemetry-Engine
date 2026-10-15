import time
from fastapi import APIRouter
from typing import List, Dict, Any
from app.schemas.telemetry import TelemetryStreamSnapshot
from app.services.websocket_manager import ws_telemetry
from app.services.cosmos_service import cosmos_service

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry & Threat Intelligence"])

@router.get("/snapshot", response_model=TelemetryStreamSnapshot)
async def get_telemetry_snapshot():
    sorted_lat = sorted(ws_telemetry.latencies) if ws_telemetry.latencies else [0.85]
    p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
    total = max(1, ws_telemetry.total_transactions_evaluated)

    return TelemetryStreamSnapshot(
        timestamp_ms=int(time.time() * 1000),
        tps=285.0,
        p50_latency_ms=round(p50, 3),
        p95_latency_ms=round(p95, 3),
        p99_latency_ms=round(p99, 3),
        total_evaluated=ws_telemetry.total_transactions_evaluated,
        blocked_count=ws_telemetry.blocked_count,
        flagged_count=ws_telemetry.flagged_count,
        approved_count=ws_telemetry.approved_count,
        fraud_block_rate_pct=round((ws_telemetry.blocked_count / total) * 100, 2),
        active_ws_clients=len(ws_telemetry.active_connections)
    )

@router.get("/threats")
async def list_threat_signals(limit: int = 20):
    return await cosmos_service.query_recent_threats(limit=limit)
