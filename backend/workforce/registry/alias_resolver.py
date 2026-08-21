"""Agent Alias Resolver Service (F4 Soft Migration Layer).

Phân giải các agent keys cũ sang COSA Co-Founder, Domain Agents,
Specialists, hoặc Shared Capabilities.
"""
from typing import Optional, Dict, Tuple, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import AgentAlias
from core.snowflake import generate_snowflake_id


DEFAULT_FALLBACK_ALIASES: Dict[str, Tuple[str, str]] = {
    # alias_key -> (target_type, target_key)
    "founder_agent": ("ORCHESTRATOR", "cosa"),
    "founder_copilot": ("ORCHESTRATOR", "cosa"),
    "founder": ("ORCHESTRATOR", "cosa"),
    "research_agent": ("CAPABILITY", "investigate"),
    "researcher_agent": ("CAPABILITY", "investigate"),
    "google_search": ("CAPABILITY", "investigate"),
    "seo_agent": ("SPECIALIST", "marketing.seo"),
    "content_agent": ("SPECIALIST", "marketing.content"),
    "qa_agent": ("CAPABILITY", "quality_gate"),
    "general": ("ORCHESTRATOR", "cosa"),
}


class AgentAliasResolverService:
    """Service giải quyết Alias cho AI Agent Workforce."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(
        self,
        alias_key: str,
        workspace_id: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Phân giải alias_key sang (target_type, target_key).
        
        Ưu tiên tra cứu trong bảng `agent_aliases` của workspace.
        Nếu không có, fallback về DEFAULT_FALLBACK_ALIASES hoặc giữ nguyên.
        """
        stmt = select(AgentAlias).where(
            and_(
                AgentAlias.alias_key == alias_key,
                AgentAlias.is_active.is_(True),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(
                (AgentAlias.workspace_id == workspace_id) | (AgentAlias.workspace_id.is_(None))
            )
        
        res = await self.db.execute(stmt)
        alias_record = res.scalars().first()

        if alias_record:
            return alias_record.target_type, alias_record.target_key

        if alias_key in DEFAULT_FALLBACK_ALIASES:
            return DEFAULT_FALLBACK_ALIASES[alias_key]

        # Mặc định coi như chính nó là DOMAIN_AGENT
        return "DOMAIN", alias_key

    async def register_alias(
        self,
        alias_key: str,
        target_type: str,
        target_key: str,
        workspace_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AgentAlias:
        """Đăng ký hoặc cập nhật alias."""
        stmt = select(AgentAlias).where(
            and_(
                AgentAlias.alias_key == alias_key,
                AgentAlias.workspace_id == workspace_id,
            )
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().first()

        if existing:
            existing.target_type = target_type
            existing.target_key = target_key
            existing.is_active = True
            if notes:
                existing.notes = notes
            await self.db.flush()
            return existing

        new_alias = AgentAlias(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            alias_key=alias_key,
            target_type=target_type,
            target_key=target_key,
            is_active=True,
            notes=notes,
        )
        self.db.add(new_alias)
        await self.db.flush()
        return new_alias

    async def seed_default_aliases(self, workspace_id: Optional[int] = None) -> List[AgentAlias]:
        """Khởi tạo danh sách alias mặc định nếu chưa có."""
        created = []
        for alias_key, (target_type, target_key) in DEFAULT_FALLBACK_ALIASES.items():
            record = await self.register_alias(
                alias_key=alias_key,
                target_type=target_type,
                target_key=target_key,
                workspace_id=workspace_id,
                notes=f"Default F4 alias mapping for {alias_key}",
            )
            created.append(record)
        return created
