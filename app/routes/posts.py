from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import GeneratedPost
from app.schemas import PostOut, PostUpdate

router = APIRouter(prefix="/api", tags=["posts"])


@router.get("/posts", response_model=list[PostOut])
def list_posts(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(GeneratedPost).order_by(GeneratedPost.created_at.desc())
    if status:
        query = query.filter(GeneratedPost.status == status)
    return query.all()


@router.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, update: PostUpdate, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if update.status is not None:
        post.status = update.status
    if update.title is not None:
        post.title = update.title
    if update.content is not None:
        post.content = update.content
    db.commit()
    db.refresh(post)
    return post
