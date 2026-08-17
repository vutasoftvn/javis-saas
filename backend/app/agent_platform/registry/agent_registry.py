from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_platform.models import AgentDefinition, AgentToolPermission, ToolDefinition
from app.agent_platform.registry.defaults import DEFAULT_AGENT_MANIFESTS
from app.core.snowflake import generate_snowflake_id


class AgentRegistryService:
    """Service quản lý Agent Definitions và quyền hạn Agent trong hệ thống."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_agent_by_key(self, key: str, workspace_id: Optional[int] = None) -> Optional[AgentDefinition]:
        stmt = select(AgentDefinition).where(AgentDefinition.key == key)
        if workspace_id is not None:
            stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_agents(self, workspace_id: Optional[int] = None, enabled_only: bool = False) -> List[AgentDefinition]:
        stmt = select(AgentDefinition)
        filters = []
        if workspace_id is not None:
            filters.append(AgentDefinition.workspace_id == workspace_id)
        if enabled_only:
            filters.append(AgentDefinition.enabled.is_(True))
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def register_agent(
        self,
        key: str,
        name: str,
        description: Optional[str] = None,
        agent_type: str = "specialist",
        default_model_profile: str = "reasoning",
        system_prompt_key: str = "default.system",
        risk_level: int = 1,
        workspace_id: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentDefinition:
        existing = await self.get_agent_by_key(key, workspace_id)
        if existing:
            existing.name = name
            existing.description = description
            existing.agent_type = agent_type
            existing.default_model_profile = default_model_profile
            existing.system_prompt_key = system_prompt_key
            existing.risk_level = risk_level
            if config:
                existing.config_jsonb = config
            await self.db.flush()
            return existing

        agent = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=key,
            name=name,
            description=description,
            agent_type=agent_type,
            default_model_profile=default_model_profile,
            system_prompt_key=system_prompt_key,
            risk_level=risk_level,
            enabled=True,
            config_jsonb=config or {},
        )
        self.db.add(agent)
        await self.db.flush()
        return agent

    async def seed_factory_defaults(self, workspace_id: Optional[int] = None) -> List[AgentDefinition]:
        """Khởi tạo các Agent mặc định từ manifest chuẩn."""
        seeded = []
        for manifest in DEFAULT_AGENT_MANIFESTS:
            agent = await self.register_agent(
                key=manifest["key"],
                name=manifest["name"],
                description=manifest.get("description"),
                agent_type=manifest.get("agent_type", "specialist"),
                default_model_profile=manifest.get("default_model_profile", "reasoning"),
                system_prompt_key=manifest.get("system_prompt_key", "default.system"),
                risk_level=manifest.get("risk_level", 1),
                workspace_id=workspace_id,
            )
            seeded.append(agent)
        return seeded
