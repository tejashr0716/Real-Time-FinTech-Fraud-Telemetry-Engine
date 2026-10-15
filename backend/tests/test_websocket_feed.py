import pytest
import json
from unittest.mock import AsyncMock
from app.services.websocket_manager import WebSocketTelemetryManager

@pytest.mark.asyncio
async def test_websocket_telemetry_handshake_and_broadcast():
    manager = WebSocketTelemetryManager()

    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    # 1. Connect
    await manager.connect(mock_ws)
    assert len(manager.active_connections) == 1

    # Verify handshake sent
    mock_ws.accept.assert_awaited_once()
    assert mock_ws.send_text.await_count >= 1
    call_args = mock_ws.send_text.call_args_list[0][0][0]
    data = json.loads(call_args)
    assert data["event"] == "TELEMETRY_HANDSHAKE"

    # 2. Broadcast threat alert
    alert_json = json.dumps({"event": "THREAT_BLOCKED", "tx_id": "test_99"})
    await manager.broadcast_event(alert_json)

    assert mock_ws.send_text.await_count >= 2
    assert "THREAT_BLOCKED" in mock_ws.send_text.call_args_list[1][0][0]

    # 3. Disconnect
    await manager.disconnect(mock_ws)
    assert len(manager.active_connections) == 0
