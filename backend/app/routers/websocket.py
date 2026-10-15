import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_telemetry

logger = logging.getLogger("fraud_ws_router")
router = APIRouter(tags=["WebSocket Stream"])

@router.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    await ws_telemetry.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().upper() == "PING":
                await websocket.send_text('{"event": "PONG"}')
    except WebSocketDisconnect:
        await ws_telemetry.disconnect(websocket)
    except Exception as e:
        logger.debug(f"Client disconnected: {e}")
        await ws_telemetry.disconnect(websocket)
