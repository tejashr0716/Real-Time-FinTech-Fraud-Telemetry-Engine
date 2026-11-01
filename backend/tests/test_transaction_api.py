import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["cpp_engine_accelerated"] is True

@pytest.mark.asyncio
async def test_list_accounts(async_client):
    response = await async_client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) >= 5
    assert "balance" in accounts[0]
    assert "account_number" in accounts[0]

@pytest.mark.asyncio
async def test_list_merchants(async_client):
    response = await async_client.get("/api/merchants")
    assert response.status_code == 200
    merchants = response.json()
    assert len(merchants) >= 6
    assert any(m["id"] == "mer_apple_pay_direct" for m in merchants)

@pytest.mark.asyncio
async def test_authorize_approved_transaction(async_client):
    # Legitimate transaction on account #1
    account_id = "b0000001-0000-0000-0000-000000000001"
    idem_key = f"TEST-IDEM-{uuid.uuid4().hex[:8]}"

    payload = {
        "account_id": account_id,
        "merchant_id": "mer_apple_pay_direct",
        "amount": 199.00,
        "currency": "USD",
        "channel": "ONLINE",
        "ip_address": "198.51.100.24",
        "device_fingerprint": "fp_macbook_pro_m3_98f1",
        "geo_country": "US",
        "geo_city": "New York",
        "distance_km": 0.0,
        "time_delta_seconds": 3600.0,
        "idempotency_key": idem_key
    }

    response = await async_client.post("/api/transactions/authorize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["fraud_score"] < 40.0
    assert data["eval_latency_ms"] < 25.0

@pytest.mark.asyncio
async def test_authorize_blocked_tor_fraud_transaction(async_client):
    account_id = "b0000002-0000-0000-0000-000000000002"
    idem_key = f"TEST-IDEM-FRAUD-{uuid.uuid4().hex[:8]}"

    payload = {
        "account_id": account_id,
        "merchant_id": "mer_darknet_card_test",
        "amount": 8900.00,
        "currency": "USD",
        "channel": "CRYPTO_ONRAMP",
        "ip_address": "91.200.12.44",
        "device_fingerprint": "fp_tor_exit_node_cyber",
        "geo_country": "RU",
        "geo_city": "Moscow",
        "distance_km": 5000.0,
        "time_delta_seconds": 120.0, # Impossible travel
        "idempotency_key": idem_key
    }

    response = await async_client.post("/api/transactions/authorize", json=payload)
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "FRAUD_SECURITY_BLOCK"
    assert detail["fraud_score"] >= 75.0

@pytest.mark.asyncio
async def test_serve_dashboard(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "FraudShield Telemetry Engine" in response.text
    assert "C++ SIMD NATIVE" in response.text
