from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import AgentDefinition, AgentHierarchy, AgentToolPermission, ToolDefinition
from app.workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS
from app.core.snowflake import generate_snowflake_id


class AgentRegistryService:
    """Service quản lý Agent Definitions và Org Chart trong hệ thống COSA."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_agent_by_key(self, key: str, workspace_id: Optional[int] = None) -> Optional[AgentDefinition]:
        stmt = select(AgentDefinition).where(AgentDefinition.key == key)
        if workspace_id is not None:
            stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_agent_by_id(self, agent_id: int, workspace_id: Optional[int] = None) -> Optional[AgentDefinition]:
        stmt = select(AgentDefinition).where(AgentDefinition.id == agent_id)
        if workspace_id is not None:
            stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_agents(
        self,
        workspace_id: Optional[int] = None,
        enabled_only: bool = False,
        department: Optional[str] = None,
    ) -> List[AgentDefinition]:
        stmt = select(AgentDefinition)
        filters = []
        if workspace_id is not None:
            filters.append(AgentDefinition.workspace_id == workspace_id)
        if enabled_only:
            filters.append(AgentDefinition.enabled.is_(True))
        if department:
            filters.append(AgentDefinition.department == department)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def register_agent(
        self,
        key: str,
        name: str,
        role_title: Optional[str] = None,
        department: Optional[str] = None,
        description: Optional[str] = None,
        agent_type: str = "specialist",
        category: str = "DOMAIN",
        is_default_active: bool = False,
        default_model_profile: str = "reasoning",
        system_prompt_key: str = "default.system",
        profile_slug: Optional[str] = None,
        risk_level: int = 1,
        status: str = "idle",
        workspace_id: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        model_config: Optional[Dict[str, Any]] = None,
    ) -> AgentDefinition:
        existing = await self.get_agent_by_key(key, workspace_id)
        if existing:
            existing.name = name
            if role_title:
                existing.role_title = role_title
            if department:
                existing.department = department
            existing.description = description
            existing.agent_type = agent_type
            existing.category = category
            existing.is_default_active = is_default_active
            existing.default_model_profile = default_model_profile
            existing.system_prompt_key = system_prompt_key
            if profile_slug is not None:
                existing.profile_slug = profile_slug
            existing.risk_level = risk_level
            existing.status = status
            if config is not None:
                existing.config_jsonb = config
            if capabilities is not None:
                existing.capabilities_jsonb = capabilities
            if model_config is not None:
                existing.model_config_jsonb = model_config
            await self.db.flush()
            return existing

        agent = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=key,
            name=name,
            role_title=role_title or name,
            department=department or "General",
            description=description,
            agent_type=agent_type,
            category=category,
            is_default_active=is_default_active,
            default_model_profile=default_model_profile,
            system_prompt_key=system_prompt_key,
            profile_slug=profile_slug,
            risk_level=risk_level,
            status=status,
            enabled=True,
            config_jsonb=config or {},
            capabilities_jsonb=capabilities or {},
            model_config_jsonb=model_config or {},
        )
        self.db.add(agent)
        await self.db.flush()
        return agent

    async def get_cofounder(self, workspace_id: Optional[int] = None) -> Optional[AgentDefinition]:
        """Lấy bản ghi COSA Co-Founder (ORCHESTRATOR)."""
        stmt = select(AgentDefinition).where(
            and_(
                AgentDefinition.category == "ORCHESTRATOR",
                AgentDefinition.enabled.is_(True),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_core_domain_agents(self, workspace_id: Optional[int] = None) -> List[AgentDefinition]:
        """Lấy danh sách 5 Core Domain Agents mặc định."""
        stmt = select(AgentDefinition).where(
            and_(
                AgentDefinition.category == "DOMAIN",
                AgentDefinition.is_default_active.is_(True),
                AgentDefinition.enabled.is_(True),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())


    async def update_agent_status(self, key: str, status: str, workspace_id: Optional[int] = None) -> Optional[AgentDefinition]:
        agent = await self.get_agent_by_key(key, workspace_id)
        if agent:
            agent.status = status
            await self.db.flush()
        return agent

    async def set_hierarchy(
        self,
        child_agent_id: int,
        parent_agent_id: Optional[int],
        workspace_id: Optional[int] = None,
        relationship_type: str = "REPORTS_TO",
    ) -> AgentHierarchy:
        # Xóa quan hệ cũ nếu có
        del_stmt = delete(AgentHierarchy).where(
            and_(
                AgentHierarchy.child_agent_id == child_agent_id,
                AgentHierarchy.workspace_id == workspace_id,
            )
        )
        await self.db.execute(del_stmt)

        hierarchy = AgentHierarchy(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            parent_agent_id=parent_agent_id,
            child_agent_id=child_agent_id,
            relationship_type=relationship_type,
        )
        self.db.add(hierarchy)
        await self.db.flush()
        return hierarchy

    async def get_org_chart(self, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        agents = await self.list_agents(workspace_id=workspace_id, enabled_only=True)
        agents_map = {a.id: a for a in agents}
        key_to_id = {a.key: a.id for a in agents}

        stmt = select(AgentHierarchy)
        if workspace_id is not None:
            stmt = stmt.where(AgentHierarchy.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        hierarchies = list(res.scalars().all())

        parent_child_map: Dict[Optional[int], List[int]] = {}
        for h in hierarchies:
            parent_child_map.setdefault(h.parent_agent_id, []).append(h.child_agent_id)

        # Build tree representation
        def build_node(agent_id: int) -> Dict[str, Any]:
            ag = agents_map.get(agent_id)
            if not ag:
                return {}
            children_ids = parent_child_map.get(agent_id, [])
            return {
                "id": ag.id,
                "key": ag.key,
                "name": ag.name,
                "role_title": ag.role_title,
                "department": ag.department,
                "agent_type": ag.agent_type,
                "model_profile": ag.default_model_profile,
                "risk_level": ag.risk_level,
                "status": ag.status,
                "children": [build_node(cid) for cid in children_ids if cid in agents_map],
            }

        # Roots are nodes where parent_agent_id is None
        root_agent_ids = parent_child_map.get(None, [])
        if not root_agent_ids:
            # Fallback: founder_copilot or founder is root
            for k in ["founder_copilot", "founder"]:
                if k in key_to_id:
                    root_agent_ids = [key_to_id[k]]
                    break

        if not root_agent_ids and agents:
            root_agent_ids = [agents[0].id]

        return [build_node(rid) for rid in root_agent_ids if rid in agents_map]

    async def delete_agent(self, key_or_id: Any, workspace_id: Optional[int] = None) -> bool:
        """Xóa Custom Agent (không cho phép xóa 12 System Default Agents)."""
        system_keys = {m["key"] for m in DEFAULT_AGENT_MANIFESTS}
        
        agent = None
        if isinstance(key_or_id, int) or (isinstance(key_or_id, str) and key_or_id.isdigit()):
            agent = await self.get_agent_by_id(int(key_or_id), workspace_id)
        else:
            agent = await self.get_agent_by_key(str(key_or_id), workspace_id)

        if not agent:
            raise ValueError(f"Agent '{key_or_id}' không tồn tại")

        if agent.key in system_keys or (agent.config_jsonb and agent.config_jsonb.get("is_system") is True):
            raise ValueError(f"Không thể xóa System Agent cốt lõi '{agent.name}'")

        # 1. Xóa quan hệ Org Chart
        del_h_stmt = delete(AgentHierarchy).where(
            and_(
                (AgentHierarchy.child_agent_id == agent.id) | (AgentHierarchy.parent_agent_id == agent.id),
                AgentHierarchy.workspace_id == workspace_id if workspace_id is not None else True
            )
        )
        await self.db.execute(del_h_stmt)

        # 2. Xóa Agent Definition
        del_stmt = delete(AgentDefinition).where(AgentDefinition.id == agent.id)
        await self.db.execute(del_stmt)
        await self.db.flush()
        return True

    async def clone_agent(
        self,
        source_key: str,
        new_key: str,
        new_name: str,
        workspace_id: Optional[int] = None,
    ) -> AgentDefinition:
        """Nhân bản một Agent có sẵn thành Custom Agent mới."""
        source = await self.get_agent_by_key(source_key, workspace_id)
        if not source:
            source = await self.get_agent_by_key(source_key, None)
        if not source:
            raise ValueError(f"Source agent '{source_key}' không tồn tại")

        custom_config = dict(source.config_jsonb or {})
        custom_config["is_system"] = False
        custom_config["cloned_from"] = source.key

        new_agent = await self.register_agent(
            key=new_key,
            name=new_name,
            role_title=f"{source.role_title} (Custom)",
            department=source.department,
            description=f"Nhân bản từ {source.name}. {source.description or ''}",
            agent_type=source.agent_type,
            default_model_profile=source.default_model_profile,
            system_prompt_key=source.system_prompt_key,
            risk_level=source.risk_level,
            status="idle",
            workspace_id=workspace_id,
            config=custom_config,
            capabilities=dict(source.capabilities_jsonb or {}),
            model_config=dict(source.model_config_jsonb or {}),
        )
        return new_agent

    async def seed_factory_defaults(self, workspace_id: Optional[int] = None) -> List[AgentDefinition]:
        """Khởi tạo các Agent và Org Chart mặc định từ manifest chuẩn."""
        seeded = []
        key_to_agent: Dict[str, AgentDefinition] = {}

        # 1. Register agents
        for manifest in DEFAULT_AGENT_MANIFESTS:
            config = dict(manifest.get("config", {}))
            config["is_system"] = True
            agent = await self.register_agent(
                key=manifest["key"],
                name=manifest["name"],
                role_title=manifest.get("role_title"),
                department=manifest.get("department"),
                description=manifest.get("description"),
                agent_type=manifest.get("agent_type", "specialist"),
                category=manifest.get("category", "DOMAIN"),
                is_default_active=manifest.get("is_default_active", False),
                default_model_profile=manifest.get("default_model_profile", "reasoning"),
                system_prompt_key=manifest.get("system_prompt_key", "default.system"),
                risk_level=manifest.get("risk_level", 1),
                workspace_id=workspace_id,
                config=config,
            )
            seeded.append(agent)
            key_to_agent[manifest["key"]] = agent

        # 2. Build default hierarchy
        for manifest in DEFAULT_AGENT_MANIFESTS:
            child_key = manifest["key"]
            parent_key = manifest.get("parent_key")
            if child_key in key_to_agent:
                child_id = key_to_agent[child_key].id
                parent_id = key_to_agent[parent_key].id if parent_key and parent_key in key_to_agent else None
                await self.set_hierarchy(
                    child_agent_id=child_id,
                    parent_agent_id=parent_id,
                    workspace_id=workspace_id,
                )

        return seeded

