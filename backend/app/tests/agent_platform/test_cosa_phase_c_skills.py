import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.workforce.models import ToolDefinition, PlatformToolVersion, PlatformPromptTemplate, PlatformPromptVersion, AgentDefinition
from app.workforce.skills.skill_registry import SkillRegistryService
from app.workforce.skills.skill_loader import DynamicSkillLoader
from app.workforce.skills.versioning import SkillVersioningService
from app.workforce.dispatcher.context_builder import AgentContextBuilder
from app.founder_os.tasks.models import Task


class TestDynamicSkillLoader:
    """Kiểm thử DynamicSkillLoader cấp phát schema tools động theo quyền hạn."""

    @pytest.mark.asyncio
    async def test_dynamic_tool_loading_for_agent(self):
        mock_db = AsyncMock()
        tool1 = ToolDefinition(
            id=1,
            key="crm.search",
            name="Search CRM",
            transport="local",
            risk_level=0,
            enabled=True,
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )
        tool2 = ToolDefinition(
            id=2,
            key="finance.post_entry",
            name="Post Entry",
            transport="local",
            risk_level=4,
            enabled=True,
        )

        mock_tools_res = MagicMock()
        mock_tools_res.scalars().all.return_value = [tool1, tool2]
        mock_db.execute.return_value = mock_tools_res

        agent = AgentDefinition(id=101, key="sales_agent", name="Sales Agent")

        loader = DynamicSkillLoader(mock_db)
        # Mock permission engine: crm.search is allowed, finance.post_entry is not allowed for sales
        async def mock_can(principal_type, principal_id, resource_type, resource_key, action, workspace_id):
            return resource_key == "crm.search"

        loader.permission_engine.can = mock_can

        schemas = await loader.load_tools_for_agent(agent, workspace_id=1)
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "crm.search"
        assert schemas[0]["type"] == "function"


class TestSkillVersioningAndDiff:
    """Kiểm thử cơ chế Versioning và Diffing cho Tool Spec và Prompt."""

    @pytest.mark.asyncio
    async def test_tool_spec_versioning(self):
        mock_db = AsyncMock()
        tool = ToolDefinition(
            id=10,
            key="email.send",
            name="Send Email",
            version=1,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            config_jsonb={"timeout": 30},
        )
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = tool
        mock_db.execute.return_value = mock_res

        service = SkillVersioningService(mock_db)
        updated_tool = await service.update_tool_spec(
            key="email.send",
            input_schema={"type": "object", "properties": {"to": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            config={"timeout": 60},
            change_note="Added 'to' recipient parameter",
        )

        assert updated_tool.version == 2
        assert updated_tool.config_jsonb["timeout"] == 60
        # Version 1 was saved to PlatformToolVersion
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_prompt_diff_generation(self):
        mock_db = AsyncMock()
        tmpl = PlatformPromptTemplate(
            id=20,
            key="founder.system",
            default_content="Line 1: Default Founder System Prompt.\nLine 2: Rule A.",
            current_content="Line 1: Default Founder System Prompt.\nLine 2: Modified Rule A with extra power.",
            current_version=2,
        )
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = tmpl
        mock_db.execute.return_value = mock_res

        service = SkillVersioningService(mock_db)
        diff_res = await service.get_prompt_diff("founder.system")

        assert diff_res["is_modified_from_default"] is True
        assert "Modified Rule A with extra power" in diff_res["diff_text"]


class TestResetToDefault:
    """Kiểm thử tính năng Reset to Default khôi phục cấu hình gốc."""

    @pytest.mark.asyncio
    async def test_reset_tool_to_factory_default(self):
        mock_db = AsyncMock()
        tool = ToolDefinition(
            id=15,
            key="google.search",
            name="Google Search Custom",
            version=3,
            config_jsonb={"custom_key": "val"},
        )
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = tool
        mock_db.execute.return_value = mock_res

        service = SkillVersioningService(mock_db)
        reset_tool = await service.reset_tool_to_default(key="google.search")

        assert reset_tool.version == 4
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_prompt_to_default(self):
        mock_db = AsyncMock()
        tmpl = PlatformPromptTemplate(
            id=25,
            key="general.system",
            default_content="Bạn là COSA General Assistant chuẩn.",
            current_content="Bạn là bot tùy biến.",
            current_version=4,
        )
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = tmpl
        mock_db.execute.return_value = mock_res

        service = SkillVersioningService(mock_db)
        reset_tmpl = await service.reset_prompt_to_default("general.system")

        assert reset_tmpl.current_content == "Bạn là COSA General Assistant chuẩn."
        assert reset_tmpl.current_version == 5


class TestFourLayersSeparation:
    """Kiểm thử tách bạch 4 lớp (Prompt, Skill, Policy, Spec) trong Context Builder."""

    @pytest.mark.asyncio
    async def test_four_layers_assembled_into_payload(self):
        mock_db = AsyncMock()
        agent = AgentDefinition(
            id=1,
            key="cfo_agent",
            name="CFO Agent",
            system_prompt_key="finance.system",
            risk_level=2,
            workspace_id=1,
            model_config_jsonb={"model": "claude-3-5-sonnet-20241022", "temperature": 0.1},
        )
        task = Task(
            id=301,
            workspace_id=1,
            title="Kiểm toán ngân sách 12WY",
            status="todo",
            priority="urgent",
        )

        builder = AgentContextBuilder(mock_db)
        # Mock prompt registry (Prompt Layer)
        builder.prompt_registry.get_prompt_content = AsyncMock(return_value="System Prompt for CFO")
        # Mock dynamic skill loader (Skill Layer)
        builder.skill_loader.load_tools_for_agent = AsyncMock(return_value=[
            {"type": "function", "function": {"name": "finance.read_summary"}}
        ])

        payload = await builder.build_task_payload(agent, task, extra_context={"Q": "Q3"})

        assert payload.agent_key == "cfo_agent"
        assert payload.messages[0].content == "System Prompt for CFO"
        assert "Kiểm toán ngân sách 12WY" in payload.messages[1].content
        assert len(payload.tools_schema) == 1
        assert payload.tools_schema[0]["function"]["name"] == "finance.read_summary"
