"""Unit Tests for Phase 1: Database Schema & Migration Layer (F4 Spec).

Verifies:
1. AgentDefinition category & is_default_active attributes.
2. COSA Co-Founder (ORCHESTRATOR) vs 5 Core Domain Agents (DOMAIN).
3. FounderDecision model, schema & FounderDecisionService lifecycle.
4. AgentAlias model, schema & AgentAliasResolverService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.workforce.models import AgentDefinition, FounderDecision, AgentAlias
from app.workforce.schemas.agent_category_schemas import AgentCategoryEnum
from app.workforce.schemas.decision_schemas import (
    FounderDecisionCreate,
    FounderDecisionResolveRequest,
    DecisionStatusEnum,
    DecisionDomainEnum,
    DecisionOption,
)
from app.workforce.registry.agent_registry import AgentRegistryService
from app.workforce.registry.alias_resolver import AgentAliasResolverService
from app.workforce.governance.founder_decision_service import FounderDecisionService


class TestCosaPhase1Schema:
    """Kiểm thử mô hình dữ liệu và dịch vụ của Phase 1."""

    @pytest.mark.asyncio
    async def test_agent_definition_category_attributes(self):
        """Kiểm tra thuộc tính category và is_default_active trên AgentDefinition."""
        agent = AgentDefinition(
            id=1001,
            workspace_id=1,
            key="cosa",
            name="COSA Co-Founder",
            category=AgentCategoryEnum.ORCHESTRATOR.value,
            is_default_active=True,
            agent_type="orchestrator",
        )
        assert agent.category == "ORCHESTRATOR"
        assert agent.is_default_active is True
        assert agent.key == "cosa"

    @pytest.mark.asyncio
    async def test_agent_registry_cofounder_and_core_domains(self):
        """Kiểm tra AgentRegistryService phân biệt Co-Founder và 5 Core Domain Agents."""
        db_mock = AsyncMock()

        # Mock query return values
        cosa_agent = AgentDefinition(
            id=1,
            key="cosa",
            name="COSA Co-Founder",
            category="ORCHESTRATOR",
            is_default_active=True,
            enabled=True,
        )
        core_agents = [
            AgentDefinition(id=2, key="cfo_agent", name="Finance Agent", category="DOMAIN", is_default_active=True, enabled=True),
            AgentDefinition(id=3, key="cmo_agent", name="Marketing Agent", category="DOMAIN", is_default_active=True, enabled=True),
            AgentDefinition(id=4, key="sales_agent", name="Sales Agent", category="DOMAIN", is_default_active=True, enabled=True),
            AgentDefinition(id=5, key="tech_lead_agent", name="Build Agent", category="DOMAIN", is_default_active=True, enabled=True),
            AgentDefinition(id=6, key="legal_agent", name="Legal Agent", category="DOMAIN", is_default_active=True, enabled=True),
        ]

        registry = AgentRegistryService(db_mock)

        # Test get_cofounder
        mock_res_cofounder = MagicMock()
        mock_res_cofounder.scalars.return_value.first.return_value = cosa_agent
        db_mock.execute.return_value = mock_res_cofounder

        cofounder = await registry.get_cofounder(workspace_id=1)
        assert cofounder is not None
        assert cofounder.key == "cosa"
        assert cofounder.category == "ORCHESTRATOR"

        # Test list_core_domain_agents
        mock_res_core = MagicMock()
        mock_res_core.scalars.return_value.all.return_value = core_agents
        db_mock.execute.return_value = mock_res_core

        domains = await registry.list_core_domain_agents(workspace_id=1)
        assert len(domains) == 5
        assert all(d.category == "DOMAIN" for d in domains)
        assert all(d.is_default_active is True for d in domains)

    @pytest.mark.asyncio
    async def test_founder_decision_service_lifecycle(self):
        """Kiểm tra vòng đời tạo, lấy hàng đợi và chốt quyết định của Founder."""
        db_mock = AsyncMock()
        service = FounderDecisionService(db_mock)

        # 1. Create Decision
        create_payload = FounderDecisionCreate(
            workspace_id=10,
            project_id=20,
            domain=DecisionDomainEnum.MARKETING,
            question="Có nên tăng ngân sách chiến dịch Acquisition lên 50 triệu?",
            context_summary="Marketing Agent đề xuất mở rộng kênh Paid Ads, nhưng cần đối chiếu Cashflow.",
            options_jsonb=[
                DecisionOption(id="A", title="Tăng 50tr như đề xuất", pros=["Mở rộng lead"], cons=["Giảm runway 1 tuần"]),
                DecisionOption(id="B", title="Thử nghiệm trước 15tr", pros=["Kiểm chứng CAC trước"], cons=["Quy mô chậm hơn"]),
            ],
            ai_recommendation_jsonb={
                "recommended_option_id": "B",
                "confidence": 0.9,
                "rationale": "Kiểm chứng CAC trước trên tệp nhỏ phù hợp với Runway hiện tại.",
            },
            evidence_ids=["evi_problem_01", "evi_interview_04"],
            risk_analysis_jsonb={"level": "MEDIUM", "runway_impact_weeks": -1},
        )

        decision = await service.create_decision(create_payload)
        assert decision.question == create_payload.question
        assert decision.status == "PENDING"
        assert len(decision.evidence_ids) == 2
        assert len(decision.options_jsonb) == 2

        # 2. Resolve Decision
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = decision
        db_mock.execute.return_value = mock_res

        resolve_payload = FounderDecisionResolveRequest(
            decision_made="Chọn phương án B: Thử nghiệm trước 15tr",
            founder_notes="Đồng ý với phân tích của COSA, ưu tiên an toàn dòng tiền.",
            status=DecisionStatusEnum.DECIDED,
        )

        resolved = await service.resolve_decision(
            decision_id=decision.id,
            resolve_data=resolve_payload,
            user_id=999,
            workspace_id=10,
        )

        assert resolved is not None
        assert resolved.status == "DECIDED"
        assert resolved.decision_made == "Chọn phương án B: Thử nghiệm trước 15tr"
        assert resolved.decided_by_user_id == 999
        assert resolved.decided_at is not None

    @pytest.mark.asyncio
    async def test_agent_alias_resolver_service(self):
        """Kiểm tra phân giải Alias mềm cho các Agent cũ."""
        db_mock = AsyncMock()
        # Mock DB không có alias tuỳ biến -> fallback default
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        db_mock.execute.return_value = mock_res

        resolver = AgentAliasResolverService(db_mock)

        # Test fallback aliases
        target_type, target_key = await resolver.resolve("founder_agent")
        assert target_type == "ORCHESTRATOR"
        assert target_key == "cosa"

        target_type, target_key = await resolver.resolve("research_agent")
        assert target_type == "CAPABILITY"
        assert target_key == "investigate"

        target_type, target_key = await resolver.resolve("seo_agent")
        assert target_type == "SPECIALIST"
        assert target_key == "marketing.seo"

        target_type, target_key = await resolver.resolve("qa_agent")
        assert target_type == "CAPABILITY"
        assert target_key == "quality_gate"

        # Unknown agent -> defaults to DOMAIN with same key
        target_type, target_key = await resolver.resolve("custom_new_domain")
        assert target_type == "DOMAIN"
        assert target_key == "custom_new_domain"
