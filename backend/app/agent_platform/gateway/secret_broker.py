import os
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_platform.models import PlatformSecretRef


class SecretBroker:
    """Secret Broker bảo mật thông tin xác thực, ngăn chặn rò rỉ API key vào LLM context."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_secret(self, provider: str, key_name: str, workspace_id: Optional[int] = None) -> Optional[str]:
        # 1. Tra cứu trong DB PlatformSecretRef nếu có
        stmt = select(PlatformSecretRef).where(
            and_(
                PlatformSecretRef.provider == provider,
                PlatformSecretRef.key_name == key_name
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(PlatformSecretRef.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        record = res.scalars().first()
        if record and record.external_ref:
            # Nếu là env reference
            if record.external_ref.startswith("env:"):
                env_var = record.external_ref.replace("env:", "").strip()
                return os.environ.get(env_var)
            return record.external_ref

        # 2. Fallback về Environment Variables
        env_candidates = [
            f"{provider.upper()}_{key_name.upper()}",
            f"{key_name.upper()}",
            f"{provider.upper()}_API_KEY",
        ]
        for candidate in env_candidates:
            val = os.environ.get(candidate)
            if val:
                return val

        return None
