"""WebSocket endpoint for real-time notifications."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.core.ws_manager import authenticate_ws_token, notification_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = ""):
    """Real-time notification push. Auth via first message or ?token."""
    await websocket.accept()

    payload = None
    if token:
        payload = authenticate_ws_token(token)

    if not payload:
        try:
            first_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            if first_msg.get("type") == "auth" and first_msg.get("token"):
                payload = authenticate_ws_token(first_msg["token"])
        except Exception:
            pass

    if not payload:
        await websocket.close(code=4001, reason="Authentication required")
        return

    user_id = payload["sub"]
    notification_manager.connections[user_id] = websocket

    try:
        while True:
            # Client can send heartbeat pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id)
    except Exception:
        notification_manager.disconnect(user_id)
