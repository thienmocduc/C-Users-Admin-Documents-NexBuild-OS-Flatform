"""WebSocket connection managers for chat, notifications, and GPS."""
import json
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from jose import JWTError


class ConnectionManager:
    """Generic WebSocket connection manager."""

    def __init__(self):
        # room_id -> set of (user_id, websocket) tuples
        self.rooms: dict[str, set[tuple[str, WebSocket]]] = {}

    async def connect(self, room_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add((user_id, websocket))

    def disconnect(self, room_id: str, user_id: str, websocket: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id].discard((user_id, websocket))
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    async def broadcast(self, room_id: str, message: dict, exclude_user: str = None):
        """Send message to all connections in a room."""
        if room_id not in self.rooms:
            return
        disconnected = []
        for user_id, ws in self.rooms[room_id]:
            if exclude_user and user_id == exclude_user:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append((user_id, ws))
        for item in disconnected:
            self.rooms[room_id].discard(item)

    async def send_to_user(self, room_id: str, user_id: str, message: dict):
        """Send message to a specific user in a room."""
        if room_id not in self.rooms:
            return
        for uid, ws in self.rooms[room_id]:
            if uid == user_id:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


class UserConnectionManager:
    """WebSocket manager keyed by user_id (for notifications)."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.connections.pop(user_id, None)

    async def send_notification(self, user_id: str, data: dict):
        """Push notification to connected user."""
        ws = self.connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.connections.pop(user_id, None)


def authenticate_ws_token(token: str) -> Optional[dict]:
    """Validate JWT token from WebSocket query param."""
    from api.core.security import decode_token
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


# Singleton instances
chat_manager = ConnectionManager()
notification_manager = UserConnectionManager()
gps_manager = ConnectionManager()
