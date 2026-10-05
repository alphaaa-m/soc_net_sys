"""Text helpers (Phase 5). Stubbed in Phase 0 with the agreed normalisation rules."""

import re

HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]{1,50})")
MENTION_RE = re.compile(r"@([A-Za-z0-9_]{3,30})")


def extract_hashtags(content: str) -> list[str]:
    """Return lowercase hashtag names without '#', deduplicated, order preserved."""
    seen: list[str] = []
    for m in HASHTAG_RE.findall(content or ""):
        name = m.lower()
        if name not in seen:
            seen.append(name)
    return seen


def extract_mentions(content: str, limit: int = 10) -> list[str]:
    """Return lowercase mentioned usernames, deduplicated, capped at `limit`."""
    seen: list[str] = []
    for m in MENTION_RE.findall(content or ""):
        name = m.lower()
        if name not in seen:
            seen.append(name)
        if len(seen) >= limit:
            break
    return seen
