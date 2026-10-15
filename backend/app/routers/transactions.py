import time
import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.cpp_engine import cpp_engine
from app.services.redis_service import redis_service
from app.services.rabbitmq_service import rabbitmq_service
from app.services.database_service import db_service
from app.services.cosmos_service import cosmos_service
from app.services.websocket_manager import ws_telemetry

router = APIRouter(prefix="/api/transactions", tags=["Transaction Authorization & Fraud Engine"])

@router.post("/authorize", response_model=TransactionResponse)
async def authorize_transaction(tx: TransactionCreate):
    t0 = time.perf_counter()
    now_ms = int(time.time() * 1000)

    # 1. Fetch Account Baseline & Merchant Risk Weight from PostgreSQL / Azure SQL
    account = await db_service.fetchrow(
        "SELECT id, balance, avg_daily_spend, status FROM accounts WHERE id = $1",
        uuid.UUID(tx.account_id)
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account["status"] in ("FROZEN", "RESTRICTED"):
        raise HTTPException(status_code=403, detail=f"Account is {account['status']}. Transactions prohibited.")

    merchant = await db_service.fetchrow(
        "SELECT id, name, default_risk_weight, category FROM merchants WHERE id = $1",
        tx.merchant_id
    )
    merchant_weight = float(merchant["default_risk_weight"]) if merchant else 1.0

    # 2. Redis In-Memory Velocity & Blacklist Evaluation
    is_blacklisted = await redis_service.is_ip_blacklisted(tx.ip_address)
    velocity_count = await redis_service.record_and_get_velocity(
        account_id=tx.account_id,
        tx_id=tx.idempotency_key,
        now_ms=now_ms,
        window_seconds=60
    )

    # 3. High-Performance C++ Native SIMD Rule Evaluation
    score, decision, primary_rule, eval_us, c_acc = cpp_engine.evaluate(
        amount=tx.amount,
        account_avg_daily_spend=float(account["avg_daily_spend"]),
        merchant_risk_weight=merchant_weight,
        velocity_60s_count=velocity_count,
        is_tor_or_proxy=is_blacklisted or ("tor" in tx.device_fingerprint.lower()),
        is_new_device=("new" in tx.device_fingerprint.lower()),
        distance_km=tx.distance_km,
        time_delta_seconds=tx.time_delta_seconds
    )

    t1 = time.perf_counter()
    total_eval_ms = round((t1 - t0) * 1000.0, 3)

    rules_triggered = [primary_rule]
    if velocity_count >= 3:
        rules_triggered.append(f"VELOCITY_BURST_COUNT_{velocity_count}")
    if is_blacklisted:
        rules_triggered.append("IP_THREAT_INTEL_BLACKLIST")

    # Record telemetry metrics
    ws_telemetry.record_metrics(decision, total_eval_ms)

    tx_id = uuid.uuid4()

    # 4. Handle Decisions
    if decision == "BLOCKED":
        # Log to Cosmos DB & RabbitMQ High Priority Fraud Queue
        threat_doc = {
            "transaction_id": str(tx_id),
            "account_id": tx.account_id,
            "merchant_id": tx.merchant_id,
            "amount": tx.amount,
            "fraud_score": score,
            "primary_rule": primary_rule,
            "rules_triggered": rules_triggered,
            "ip_address": tx.ip_address,
            "device_fingerprint": tx.device_fingerprint,
            "geo_country": tx.geo_country,
            "geo_city": tx.geo_city,
            "eval_latency_us": eval_us
        }
        await cosmos_service.insert_threat_document(threat_doc)
        await rabbitmq_service.publish_transaction_event("transaction.fraud.alert", threat_doc)

        # Broadcast live threat alert to WebSocket dashboards
        await redis_service.publish_telemetry_event({
            "event": "THREAT_BLOCKED",
            "transaction_id": str(tx_id),
            "account_id": tx.account_id,
            "amount": tx.amount,
            "fraud_score": score,
            "primary_rule": primary_rule,
            "geo_city": tx.geo_city,
            "geo_country": tx.geo_country,
            "timestamp": now_ms
        })

        # Persist blocked record in DB for auditing
        await db_service.execute(
            """INSERT INTO transactions (id, account_id, merchant_id, amount, currency, channel,
                                        ip_address, device_fingerprint, geo_country, geo_city,
                                        fraud_score, decision, rules_triggered, eval_latency_ms, idempotency_key)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'BLOCKED', $12, $13, $14)
               ON CONFLICT (idempotency_key) DO NOTHING""",
            tx_id, uuid.UUID(tx.account_id), tx.merchant_id, tx.amount, tx.currency, tx.channel,
            tx.ip_address, tx.device_fingerprint, tx.geo_country, tx.geo_city,
            score, rules_triggered, total_eval_ms, tx.idempotency_key
        )

        raise HTTPException(
            status_code=403,
            detail={
                "code": "FRAUD_SECURITY_BLOCK",
                "message": f"Transaction blocked by AI fraud engine. Score: {score}/100. Rule: {primary_rule}",
                "transaction_id": str(tx_id),
                "fraud_score": score,
                "primary_rule": primary_rule
            }
        )

    # 5. ACID Settlement: Deduct balance in PostgreSQL
    if float(account["balance"]) < tx.amount:
        raise HTTPException(status_code=400, detail="Insufficient account funds for settlement")

    await db_service.execute(
        """UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1""",
        tx.amount, uuid.UUID(tx.account_id)
    )

    # Insert authorized transaction
    await db_service.execute(
        """INSERT INTO transactions (id, account_id, merchant_id, amount, currency, channel,
                                    ip_address, device_fingerprint, geo_country, geo_city,
                                    fraud_score, decision, rules_triggered, eval_latency_ms, idempotency_key)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
           ON CONFLICT (idempotency_key) DO NOTHING""",
        tx_id, uuid.UUID(tx.account_id), tx.merchant_id, tx.amount, tx.currency, tx.channel,
        tx.ip_address, tx.device_fingerprint, tx.geo_country, tx.geo_city,
        score, decision, rules_triggered, total_eval_ms, tx.idempotency_key
    )

    # Publish to RabbitMQ settlement queue
    await rabbitmq_service.publish_transaction_event("transaction.settlement", {
        "transaction_id": str(tx_id),
        "account_id": tx.account_id,
        "amount": tx.amount,
        "decision": decision
    })

    # Broadcast approval to WebSocket stream
    await redis_service.publish_telemetry_event({
        "event": "TRANSACTION_AUTHORIZED",
        "transaction_id": str(tx_id),
        "amount": tx.amount,
        "fraud_score": score,
        "decision": decision,
        "primary_rule": primary_rule,
        "timestamp": now_ms
    })

    return TransactionResponse(
        id=str(tx_id),
        account_id=tx.account_id,
        merchant_id=tx.merchant_id,
        amount=tx.amount,
        currency=tx.currency,
        channel=tx.channel,
        ip_address=tx.ip_address,
        device_fingerprint=tx.device_fingerprint,
        geo_country=tx.geo_country,
        geo_city=tx.geo_city,
        fraud_score=score,
        decision=decision,
        rules_triggered=rules_triggered,
        eval_latency_ms=total_eval_ms,
        idempotency_key=tx.idempotency_key
    )

@router.get("", response_model=List[TransactionResponse])
async def list_transactions(limit: int = 50):
    rows = await db_service.fetch(
        """SELECT id, account_id, merchant_id, amount, currency, channel,
                  ip_address, device_fingerprint, geo_country, geo_city,
                  fraud_score, decision, rules_triggered, eval_latency_ms, idempotency_key, created_at
           FROM transactions
           ORDER BY created_at DESC
           LIMIT $1""",
        limit
    )
    return [
        TransactionResponse(
            id=str(r["id"]),
            account_id=str(r["account_id"]),
            merchant_id=r["merchant_id"],
            amount=float(r["amount"]),
            currency=r["currency"],
            channel=r["channel"],
            ip_address=r["ip_address"],
            device_fingerprint=r["device_fingerprint"],
            geo_country=r["geo_country"],
            geo_city=r["geo_city"],
            fraud_score=float(r["fraud_score"]),
            decision=r["decision"],
            rules_triggered=r["rules_triggered"] or [],
            eval_latency_ms=float(r["eval_latency_ms"]),
            idempotency_key=r["idempotency_key"],
            created_at=r["created_at"]
        )
        for r in rows
    ]
