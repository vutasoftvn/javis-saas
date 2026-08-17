from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_platform.models import ToolDefinition, AgentToolPermission
from app.agent_platform.registry.defaults import DEFAULT_TOOL_MANIFESTS
from app.core.snowflake import generate_snowflake_id


class ToolRegistryService:
    """Service quản lý Tool Definitions và tra cứu công cụ tập trung."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tool_by_key(self, key: str, workspace_id: Optional[int] = None) -> Optional[ToolDefinition]:
        stmt = select(ToolDefinition).where(ToolDefinition.key == key)
        if workspace_id is not None:
            stmt = stmt.where(ToolDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_tools(
        self,
        workspace_id: Optional[int] = None,
        transport: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[ToolDefinition]:
        stmt = select(ToolDefinition)
        filters = []
        if workspace_id is not None:
            filters.append(ToolDefinition.workspace_id == workspace_id)
        if transport is not None:
            filters.append(ToolDefinition.transport == transport)
        if enabled_only:
            filters.append(ToolDefinition.enabled.is_(True))
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def register_tool(
        self,
        key: str,
        name: str,
        description: Optional[str] = None,
        transport: str = "local",
        risk_level: int = 0,
        requires_approval: bool = False,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[int] = None,
    ) -> ToolDefinition:
        existing = await self.get_tool_by_key(key, workspace_id)
        if existing:
            existing.name = name
            existing.description = description
            existing.transport = transport
            existing.risk_level = risk_level
            existing.requires_approval = requires_approval
            if input_schema is not None:
                existing.input_schema = input_schema
            if output_schema is not None:
                existing.output_schema = output_schema
            if config is not None:
                existing.config_jsonb = config
            await self.db.flush()
            return existing

        tool = ToolDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=key,
            name=name,
            description=description,
            transport=transport,
            risk_level=risk_level,
            enabled=True,
            requires_approval=requires_approval,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            config_jsonb=config or {},
        )
        self.db.add(tool)
        await self.db.flush()
        return tool

    async def seed_factory_defaults(self, workspace_id: Optional[int] = None) -> List[ToolDefinition]:
        """Khởi tạo toàn bộ Tools mặc định từ manifest chuẩn."""
        seeded = []
        for manifest in DEFAULT_TOOL_MANIFESTS:
            tool = await self.register_tool(
                key=manifest["key"],
                name=manifest["name"],
                description=manifest.get("description"),
                transport=manifest.get("transport", "local"),
                risk_level=manifest.get("risk_level", 0),
                requires_approval=manifest.get("requires_approval", False),
                workspace_id=workspace_id,
            )
            seeded.append(tool)
        return seeded
