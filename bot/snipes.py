"""What counts as a snipe: a top-level post with at least one image and at least one @person tag.

The poster is the sniper. Everyone they tagged got sniped. Tagging three people is three snipes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Slack encodes @mentions as "<@U123>" or "<@U123|name>".
MENTION_RE = re.compile(r"<@([UW][A-Z0-9]+)(?:\|[^>]*)?>")
# Plain posts, file uploads, and "also send to channel" thread replies.
COUNTED_SUBTYPES = {None, "file_share", "thread_broadcast"}


@dataclass
class Snipe:
    ts: str
    sniper: str
    targets: list[str]  # in the order they were tagged
    reactions: int


def has_image(msg: dict) -> bool:
    return any((f.get("mimetype") or "").startswith("image/") for f in msg.get("files") or [])


def mentioned_users(text: str) -> list[str]:
    seen: list[str] = []
    for uid in MENTION_RE.findall(text or ""):
        if uid not in seen:
            seen.append(uid)
    return seen


def reaction_count(msg: dict, ignore_user: str | None = None) -> int:
    """Total reactions on a message, not counting the bot's own confirmation emoji."""
    total = 0
    for r in msg.get("reactions") or []:
        total += r.get("count", len(r.get("users", [])))
        if ignore_user and ignore_user in r.get("users", []):
            total -= 1
    return total


def parse_snipe(msg: dict, is_person=lambda uid: True, bot_user: str | None = None) -> Snipe | None:
    """Returns the snipe in a channel message, or None if it isn't one.

    is_person filters out tagged bots. Tagging yourself doesn't count.
    """
    if msg.get("subtype") not in COUNTED_SUBTYPES or msg.get("bot_id"):
        return None
    # Replies inside a thread don't count (unless also sent to the channel).
    if msg.get("thread_ts") not in (None, msg.get("ts")) and msg.get("subtype") != "thread_broadcast":
        return None
    sniper = msg.get("user")
    if not sniper or not has_image(msg):
        return None
    targets = [u for u in mentioned_users(msg.get("text", "")) if u != sniper and is_person(u)]
    if not targets:
        return None
    return Snipe(msg["ts"], sniper, targets, reaction_count(msg, bot_user))
