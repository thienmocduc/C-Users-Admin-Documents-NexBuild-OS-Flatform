"""WebSocket endpoint for real-time chat."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, select

from api.core.database import async_session
from api.core.ws_manager import authenticate_ws_token, chat_manager
from api.models.community import ChatMessage, ChatParticipant

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/chat/{room_id}")
async def ws_chat(websocket: WebSocket, room_id: str, token: str = ""):
    """Real-time chat WebSocket. Auth via first message or ?token query param."""
    await websocket.accept()

    # SECURITY: Accept token from first message (preferred) or query param (fallback)
    payload = None
    if token:
        payload = authenticate_ws_token(token)

    if not payload:
        # Wait for auth message
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

    # Verify user is participant of this room
    async with async_session() as db:
        result = await db.execute(
            select(ChatParticipant).where(
                and_(
                    ChatParticipant.room_id == room_id,
                    ChatParticipant.user_id == user_id,
                )
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=4003, reason="Not a participant")
            return

    # Re-register connection (already accepted above)
    if room_id not in chat_manager.rooms:
        chat_manager.rooms[room_id] = set()
    chat_manager.rooms[room_id].add((user_id, websocket))

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue

            # Save message to database
            async with async_session() as db:
                message = ChatMessage(
                    room_id=room_id,
                    sender_id=user_id,
                    content=content,
                )
                db.add(message)
                await db.commit()
                await db.refresh(message)

                msg_data = {
                    "type": "message",
                    "id": str(message.id),
                    "room_id": room_id,
                    "sender_id": user_id,
                    "content": content,
                    "created_at": message.created_at.isoformat(),
                }

            # Broadcast to all room participants
            await chat_manager.broadcast(room_id, msg_data)

    except WebSocketDisconnect:
        chat_manager.disconnect(room_id, user_id, websocket)
    except Exception:
        chat_manager.disconnect(room_id, user_id, websocket)
