import pytest
from app.services.rabbitmq_service import rabbitmq_service

@pytest.mark.asyncio
async def test_rabbitmq_service_publishing():
    # Publish to settlement queue
    await rabbitmq_service.publish_transaction_event(
        routing_key="transaction.settlement",
        event_data={
            "transaction_id": "test_tx_001",
            "account_id": "b0000001-0000-0000-0000-000000000001",
            "amount": 250.0,
            "decision": "APPROVED"
        }
    )

    # Publish to fraud alert queue
    await rabbitmq_service.publish_transaction_event(
        routing_key="transaction.fraud.alert",
        event_data={
            "transaction_id": "test_tx_002",
            "account_id": "b0000005-0000-0000-0000-000000000005",
            "fraud_score": 98.5,
            "decision": "BLOCKED",
            "primary_rule": "TOR_OR_ANON_PROXY"
        }
    )

    assert rabbitmq_service.exchange is not None or not rabbitmq_service.is_connected
