"""WebSocket endpoint for real-time GPS tracking."""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.core.ws_manager import authenticate_ws_token, gps_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/gps/{booking_id}")
async def ws_gps(websocket: WebSocket, booking_id: str, token: str = ""):
    """Real-time GPS tracking for bookings. Worker sends coords, buyer receives.
    Connect with ?token=JWT.
    """
    payload = authenticate_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Authentication required")
        return

    user_id = payload["sub"]
    user_role = payload.get("role", "")

    await gps_manager.connect(booking_id, user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if user_role == "worker":
                # Worker sends GPS coordinates
                lat = data.get("lat")
                lng = data.get("lng")
                if lat is not None and lng is not None:
                    # Store in Redis with TTL 5 min (if available)
                    try:
                        from api.core.redis import redis_pool
                        if redis_pool:
                            import aioredis
                            redis = aioredis.from_url(str(redis_pool))
                            await redis.setex(
                                f"gps:{booking_id}",
                                300,
                                json.dumps({"lat": lat, "lng": lng, "worker_id": user_id}),
                            )
                    except Exception:
                        pass  # Redis optional for GPS

                    # Broadcast to buyer
                    await gps_manager.broadcast(
                        booking_id,
                        {
                            "type": "gps_update",
                            "booking_id": booking_id,
                            "worker_id": user_id,
                            "lat": lat,
                            "lng": lng,
                            "timestamp": data.get("timestamp"),
                        },
                        exclude_user=user_id,
                    )
            else:
                # Buyer can request current location
                if data.get("action") == "request_location":
                    await gps_manager.broadcast(
                        booking_id,
                        {"type": "location_request", "buyer_id": user_id},
                        exclude_user=user_id,
                    )

    except WebSocketDisconnect:
        gps_manager.disconnect(booking_id, user_id, websocket)
    except Exception:
        gps_manager.disconnect(booking_id, user_id, websocket)
