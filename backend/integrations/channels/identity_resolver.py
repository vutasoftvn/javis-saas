"""Multi-Channel Identity Resolver for COSA OS.

Resolves external channel accounts (Telegram ID, Zalo User ID, Email, Device UUID)
to unified COSA Person / User profiles with consistent permission levels.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResolvedIdentity:
    user_id: int
    workspace_id: int
    company_id: Optional[int]
    channel: str
    external_id: str
    is_founder: bool = False
    display_name: str = "User"
    role: str = "member"
    metadata: Dict[str, Any] = None


class ChannelIdentityResolver:
    """Resolves identities across Telegram, Zalo, Web, and Mobile channels."""

    # In-memory mapping or fallback mapping for development / offline
    _LOCAL_BINDINGS: Dict[str, Dict[str, Any]] = {
        "telegram:founder": {"user_id": 1, "workspace_id": 1, "company_id": 1, "is_founder": True, "role": "founder"},
        "zalo:founder": {"user_id": 1, "workspace_id": 1, "company_id": 1, "is_founder": True, "role": "founder"},
        "web:default": {"user_id": 1, "workspace_id": 1, "company_id": 1, "is_founder": True, "role": "founder"},
    }

    @classmethod
    def resolve(
        cls,
        channel: str,
        external_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResolvedIdentity:
        key = f"{channel}:{external_id}"
        binding = cls._LOCAL_BINDINGS.get(key)

        if binding:
            return ResolvedIdentity(
                user_id=binding["user_id"],
                workspace_id=binding["workspace_id"],
                company_id=binding.get("company_id", 1),
                channel=channel,
                external_id=external_id,
                is_founder=binding.get("is_founder", False),
                role=binding.get("role", "member"),
                metadata=metadata or {},
            )

        # Default standard resolution (default workspace 1)
        return ResolvedIdentity(
            user_id=1,
            workspace_id=1,
            company_id=1,
            channel=channel,
            external_id=external_id,
            is_founder=True,  # Default local-first mode
            role="founder",
            metadata=metadata or {},
        )

    @classmethod
    def bind_account(
        cls,
        user_id: int,
        channel: str,
        external_id: str,
        workspace_id: int = 1,
        is_founder: bool = False,
    ) -> None:
        key = f"{channel}:{external_id}"
        cls._LOCAL_BINDINGS[key] = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "company_id": workspace_id,
            "is_founder": is_founder,
            "role": "founder" if is_founder else "member",
        }
        logger.info(f"[IdentityResolver] Bound {channel} account '{external_id}' to user_id {user_id}")
