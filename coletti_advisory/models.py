from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    CLIENT = "client"
    READ_ONLY = "read_only"


class Permission(str, Enum):
    VIEW = "view"
    UPLOAD = "upload"
    ANALYZE = "analyze"
    REVIEW = "review"
    MANAGE_USERS = "manage_users"
    MANAGE_ENGAGEMENTS = "manage_engagements"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(Permission),
    Role.ANALYST: frozenset({Permission.VIEW, Permission.UPLOAD, Permission.ANALYZE, Permission.REVIEW}),
    Role.REVIEWER: frozenset({Permission.VIEW, Permission.REVIEW}),
    Role.CLIENT: frozenset({Permission.VIEW, Permission.UPLOAD}),
    Role.READ_ONLY: frozenset({Permission.VIEW}),
}


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    display_name: str
    organization_id: str
    role: Role
    engagement_ids: tuple[str, ...]
    session_id: str
    authenticated_at: str
    authenticated: bool = True

    def can(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]

    def can_access(self, engagement_id: str) -> bool:
        return engagement_id in self.engagement_ids

    def auth_context(self, engagement_id: str) -> dict[str, str]:
        if not self.can_access(engagement_id):
            raise PermissionError("Principal is not authorized for this engagement")
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "engagement_id": engagement_id,
            "role": self.role.value,
            "session_id": self.session_id,
            "authenticated_at": self.authenticated_at,
        }


@dataclass(frozen=True)
class Engagement:
    engagement_id: str
    name: str
    status: str = "ACTIVE"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_engagements(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))
