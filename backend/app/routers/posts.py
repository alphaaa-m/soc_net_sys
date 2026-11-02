"""Post HTTP layer (PRD Part D, Phase 2). Rules live in post_service."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.pagination import pagination
from app.schemas import post as post_schemas
from app.services import post_service

# No prefix: this module owns both /posts/* and /users/{username}/posts.
router = APIRouter(tags=["posts"])


@router.post(
    "/posts",
    response_model=post_schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a post",
)
def create_post(
    payload: post_schemas.PostCreate,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> post_schemas.PostRead:
    return post_service.create_post(db, current, payload.content)


@router.get(
    "/posts/{post_id}",
    response_model=post_schemas.PostRead,
    summary="Get a single post",
)
def read_post(
    post_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> post_schemas.PostRead:
    return post_service.get_post(db, post_id)


@router.patch(
    "/posts/{post_id}",
    response_model=post_schemas.PostRead,
    summary="Edit one of my posts",
)
def update_post(
    post_id: int,
    payload: post_schemas.PostUpdate,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> post_schemas.PostRead:
    return post_service.update_post(db, post_id, current, payload.content)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete one of my posts",
)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    post_service.delete_post(db, post_id, current)
    return None


@router.get(
    "/users/{username}/posts",
    response_model=post_schemas.PostPage,
    summary="List a user's personal posts (newest first)",
)
def list_user_posts(
    username: str,
    page: dict = Depends(pagination),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> post_schemas.PostPage:
    return post_service.list_user_posts(
        db,
        username,
        limit=page["limit"],
        offset=page["offset"],
    )
