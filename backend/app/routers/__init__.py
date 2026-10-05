"""Reserved router URL space (Phase 0 stubs). Real behaviour lands in Phases 1-6."""

from app.routers import (
    admin,
    auth,
    blocks,
    bookmarks,
    comments,
    feed,
    follows,
    hashtags,
    health,
    likes,
    notifications,
    posts,
    reports,
    reposts,
    search,
    users,
)

all_routers = [
    auth.router,
    users.router,
    follows.router,
    posts.router,
    comments.router,
    likes.router,
    reposts.router,
    feed.router,
    bookmarks.router,
    notifications.router,
    hashtags.router,
    search.router,
    blocks.router,
    reports.router,
    admin.router,
    health.router,
]

__all__ = ["all_routers", "health"]
