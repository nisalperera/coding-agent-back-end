from __future__ import annotations

from app.core.config import settings


def is_operator_user(user_id: str) -> bool:
    return user_id in settings.OPERATOR_USER_IDS
