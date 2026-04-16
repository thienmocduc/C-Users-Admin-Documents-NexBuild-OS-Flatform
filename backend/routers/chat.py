"""Chat router — rooms, messages."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.community import ChatMessage, ChatParticipant, ChatRoom
from api.models.user import User
from api.schemas.chat import CreateRoomRequest, MessageResponse, RoomResponse, SendMessageRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/rooms", response_model=list[RoomResponse])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Danh sách phòng chat của user hiện tại."""
    # Get rooms where user is participant
    subq = select(ChatParticipant.room_id).where(
        ChatParticipant.user_id == current_user.id
    ).subquery()

    result = await db.execute(
        select(ChatRoom)
        .where(ChatRoom.id.in_(select(subq.c.room_id)))
        .order_by(desc(ChatRoom.created_at))
    )
    rooms = result.scalars().all()

    # Build response with participants and last message
    responses = []
    for room in rooms:
        # Get participants
        p_result = await db.execute(
            select(ChatParticipant.user_id).where(ChatParticipant.room_id == room.id)
        )
        participants = [row[0] for row in p_result.all()]

        # Get last message
        msg_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()

        responses.append(RoomResponse(
            id=room.id,
            type=room.type,
            entity_type=room.entity_type,
            entity_id=room.entity_id,
            participants=participants,
            last_message=last_msg.content if last_msg else None,
            last_message_at=last_msg.created_at if last_msg else None,
            created_at=room.created_at,
        ))

    return responses


@router.post("/rooms", response_model=RoomResponse, status_code=201)
async def create_room(
    req: CreateRoomRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Tạo phòng chat mới (hoặc trả về phòng hiện có nếu đã tồn tại)."""
    if req.participant_id == current_user.id:
        raise HTTPException(400, "Không thể chat với chính mình")

    # Check participant exists
    target = await db.execute(select(User).where(User.id == req.participant_id))
    if not target.scalar_one_or_none():
        raise HTTPException(404, "User không tồn tại")

    # Check existing direct room between these 2 users
    my_rooms = select(ChatParticipant.room_id).where(
        ChatParticipant.user_id == current_user.id
    ).subquery()
    their_rooms = select(ChatParticipant.room_id).where(
        ChatParticipant.user_id == req.participant_id
    ).subquery()

    existing = await db.execute(
        select(ChatRoom).where(
            and_(
                ChatRoom.id.in_(select(my_rooms.c.room_id)),
                ChatRoom.id.in_(select(their_rooms.c.room_id)),
                ChatRoom.type == "direct",
            )
        )
    )
    room = existing.scalar_one_or_none()

    if not room:
        room = ChatRoom(type="direct", entity_type=req.entity_type, entity_id=req.entity_id)
        db.add(room)
        await db.flush()

        db.add(ChatParticipant(room_id=room.id, user_id=current_user.id))
        db.add(ChatParticipant(room_id=room.id, user_id=req.participant_id))
        await db.commit()
        await db.refresh(room)

    return RoomResponse(
        id=room.id,
        type=room.type,
        entity_type=room.entity_type,
        entity_id=room.entity_id,
        participants=[current_user.id, req.participant_id],
        last_message=None,
        last_message_at=None,
        created_at=room.created_at,
    )


@router.get("/rooms/{room_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    room_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lấy tin nhắn trong phòng (phân trang)."""
    # IDOR check: user must be participant
    participant = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == current_user.id)
        )
    )
    if not participant.scalar_one_or_none():
        raise HTTPException(403, "Bạn không phải thành viên phòng chat này")

    offset = (page - 1) * limit
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == room_id)
        .order_by(desc(ChatMessage.created_at))
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    # Enrich with sender names
    responses = []
    for msg in messages:
        user_result = await db.execute(select(User.full_name).where(User.id == msg.sender_id))
        sender_name = user_result.scalar_one_or_none()
        responses.append(MessageResponse(
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            sender_name=sender_name,
            content=msg.content,
            created_at=msg.created_at,
        ))

    return responses


@router.post("/rooms/{room_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    room_id: str,
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Gửi tin nhắn trong phòng chat."""
    # IDOR check
    participant = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == current_user.id)
        )
    )
    if not participant.scalar_one_or_none():
        raise HTTPException(403, "Bạn không phải thành viên phòng chat này")

    message = ChatMessage(
        room_id=room_id,
        sender_id=current_user.id,
        content=req.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        sender_name=current_user.full_name,
        content=message.content,
        created_at=message.created_at,
    )
