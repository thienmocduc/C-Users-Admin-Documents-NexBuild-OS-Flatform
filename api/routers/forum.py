"""Forum + Reviews + Notifications router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.community import ForumComment, ForumPost, Notification
from api.models.order import Review

# ─── Forum ────────────────────────────────────────────────

forum_router = APIRouter(prefix="/forum", tags=["Forum"])


@forum_router.get("/posts")
async def list_posts(
    sort: Optional[str] = Query("hot", pattern=r"^(hot|new)$"),
    tags: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách bài viết."""
    query = select(ForumPost)
    if tags:
        query = query.where(ForumPost.tags.contains([tags]))
    if sort == "hot":
        query = query.order_by(ForumPost.votes.desc())
    else:
        query = query.order_by(ForumPost.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    posts = result.scalars().all()
    return [
        {"id": str(p.id), "author_id": str(p.author_id), "title": p.title,
         "content": p.content[:200], "tags": p.tags, "votes": p.votes,
         "comment_count": p.comment_count, "created_at": p.created_at.isoformat()}
        for p in posts
    ]


@forum_router.get("/posts/{post_id}")
async def get_post(post_id: UUID, db: AsyncSession = Depends(get_db)):
    """Chi tiết bài viết."""
    result = await db.execute(select(ForumPost).where(ForumPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Bài viết không tồn tại")
    return {"id": str(post.id), "author_id": str(post.author_id), "title": post.title,
            "content": post.content, "tags": post.tags, "votes": post.votes,
            "comment_count": post.comment_count, "created_at": post.created_at.isoformat()}


@forum_router.post("/posts", status_code=201)
async def create_post(req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Viết bài."""
    post = ForumPost(
        author_id=current_user.id,
        title=req.get("title", ""),
        content=req.get("content", ""),
        tags=req.get("tags"),
    )
    db.add(post)
    await db.flush()
    return {"id": str(post.id), "message": "Đã đăng bài", "ok": True}


@forum_router.post("/posts/{post_id}/vote")
async def vote_post(post_id: UUID, req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Vote bài viết (+1 hoặc -1). Dùng Redis set để track."""
    result = await db.execute(select(ForumPost).where(ForumPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Bài viết không tồn tại")
    value = req.get("value", 1)
    post.votes += value
    return {"votes": post.votes}


@forum_router.get("/posts/{post_id}/comments")
async def list_comments(post_id: UUID, db: AsyncSession = Depends(get_db)):
    """Comments của bài viết."""
    result = await db.execute(select(ForumComment).where(ForumComment.post_id == post_id).order_by(ForumComment.created_at))
    comments = result.scalars().all()
    return [
        {"id": str(c.id), "author_id": str(c.author_id), "content": c.content, "created_at": c.created_at.isoformat()}
        for c in comments
    ]


@forum_router.post("/posts/{post_id}/comments", status_code=201)
async def add_comment(post_id: UUID, req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Bình luận."""
    post_r = await db.execute(select(ForumPost).where(ForumPost.id == post_id))
    post = post_r.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Bài viết không tồn tại")

    comment = ForumComment(post_id=post_id, author_id=current_user.id, content=req.get("content", ""))
    db.add(comment)
    post.comment_count = (post.comment_count or 0) + 1
    await db.flush()
    return {"id": str(comment.id), "message": "Đã bình luận"}


# ─── Reviews ──────────────────────────────────────────────

review_router = APIRouter(prefix="/reviews", tags=["Reviews"])


@review_router.post("", status_code=201)
async def create_review(req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Đánh giá (supplier/worker/product/order)."""
    review = Review(
        reviewer_id=current_user.id,
        target_type=req.get("target_type"),
        target_id=req.get("target_id"),
        stars=req.get("stars", 5),
        criteria=req.get("criteria"),
        comment=req.get("comment"),
    )
    db.add(review)
    await db.flush()
    return {"id": str(review.id), "message": "Đã đánh giá", "ok": True}


@review_router.get("")
async def list_reviews(
    target_type: str = Query(...),
    target_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách đánh giá theo target."""
    result = await db.execute(
        select(Review).where(Review.target_type == target_type, Review.target_id == target_id)
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    return [
        {"id": str(r.id), "stars": r.stars, "criteria": r.criteria,
         "comment": r.comment, "created_at": r.created_at.isoformat()}
        for r in reviews
    ]


# ─── Notifications ────────────────────────────────────────

notif_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notif_router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách thông báo."""
    query = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    notifs = result.scalars().all()
    return [
        {"id": str(n.id), "type": n.type, "title": n.title,
         "message": n.message, "link": n.link, "is_read": n.is_read,
         "created_at": n.created_at.isoformat()}
        for n in notifs
    ]


@notif_router.patch("/{notif_id}/read")
async def mark_read(notif_id: UUID, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Đánh dấu đã đọc."""
    result = await db.execute(select(Notification).where(Notification.id == notif_id, Notification.user_id == current_user.id))
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
    return {"ok": True}


@notif_router.patch("/read-all")
async def mark_all_read(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Đọc hết."""
    result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    for n in result.scalars():
        n.is_read = True
    return {"ok": True}


@notif_router.get("/unread-count")
async def unread_count(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Số thông báo chưa đọc."""
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    count = result.scalar() or 0
    return {"unread": count}
