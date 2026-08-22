"""Unit Tests for Phase 3: Domain Workforce & Shared Capabilities Standard (F4 Spec).

Verifies:
1. 5 Core Domain Manifests & Categories.
2. Shared Capability 'investigate' (replaces standalone Research Agent).
3. Cross-cutting 'QualityGatePolicy' (replaces standalone QA Agent).
4. Work Product Integration with Quality Gate evaluation.
5. Optional Packs (Operations, HR, Support) management and toggle API.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS
from workforce.capabilities.investigate_service import InvestigateService
from workforce.governance.quality_gate_policy import QualityGatePolicy
from workforce.work_product.work_product_service import WorkProductService
from workforce.models import AgentDefinition, WorkProduct
from founder_os.tasks.models import Task


class TestCosaPhase3DomainWorkforce:
    """Kiểm thử tầng Domain Workforce và Shared Capabilities."""

    def test_5_core_domain_manifests(self):
        """Xác minh 5 Core Domains có cấu hình chuẩn xác (F4 Spec)."""
        manifest_map = {m["key"]: m for m in DEFAULT_AGENT_MANIFESTS}

        # 1. Co-Founder Orchestrator
        assert "cosa" in manifest_map
        assert manifest_map["cosa"]["category"] == "ORCHESTRATOR"
        assert manifest_map["cosa"]["is_default_active"] is True

        # 2. 5 Core Domains
        core_keys = ["cfo_agent", "cmo_agent", "sales_agent", "tech_lead_agent", "legal_agent"]
        for key in core_keys:
            assert key in manifest_map, f"Missing core domain manifest: {key}"
            assert manifest_map[key]["category"] == "DOMAIN"
            assert manifest_map[key]["is_default_active"] is True

        # 3. Optional Packs
        optional_keys = ["hr_agent", "operations_agent", "support_agent"]
        for key in optional_keys:
            assert key in manifest_map, f"Missing optional pack manifest: {key}"
            assert manifest_map[key]["category"] == "OPTIONAL_DOMAIN"
            assert manifest_map[key]["is_default_active"] is False

    @pytest.mark.asyncio
    async def test_investigate_shared_capability(self):
        """Xác minh Shared Capability 'investigate' thu thập bằng chứng đa nguồn."""
        service = InvestigateService()
        
        # Test legal / web inquiry
        res_legal = await service.investigate("Nghị định 13 bảo vệ dữ liệu cá nhân", sources=["web"])
        assert len(res_legal.evidence_items) > 0
        assert res_legal.evidence_items[0].source_type == "WEB"
        assert "Nghị định" in res_legal.query

        # Test finance inquiry
        res_fin = await service.investigate("Dòng tiền và báo cáo kế toán TT58")
        assert any(e.source_type == "TT58_POLICY" for e in res_fin.evidence_items)

    def test_quality_gate_policy_evaluation(self):
        """Xác minh Cross-Cutting QualityGatePolicy đánh giá chuẩn 4 tiêu chí."""
        # 1. Poor Work Product (Quá ngắn, không số liệu, không hành động)
        eval_poor = QualityGatePolicy.evaluate_work_product(
            title="Báo cáo",
            content="Đã xong việc.",
        )
        assert eval_poor.passed is False
        assert eval_poor.quality_score < 70.0

        # 2. Good Work Product (Đầy đủ, có số liệu, có next actions)
        eval_good = QualityGatePolicy.evaluate_work_product(
            title="Kế hoạch Tăng trưởng Doanh thu Quý 3",
            content=(
                "Dựa trên khảo sát 25 khách hàng mục tiêu, tỷ lệ quan tâm đạt 80%. "
                "Doanh thu dự kiến tăng 150 triệu VNĐ trong tháng tới với CAC là 2.5 triệu. "
                "Đề xuất các bước hành động tiếp theo: "
                "1. Triển khai landing page mới. "
                "2. Gửi 50 email outreach cá nhân hóa."
            ),
            evidence_ids=["evi_123"],
        )
        assert eval_good.passed is True
        assert eval_good.quality_score >= 70.0
        assert eval_good.is_evidence_backed is True
        assert eval_good.is_actionable is True

    @pytest.mark.asyncio
    async def test_work_product_creation_with_quality_gate(self):
        """Xác minh WorkProductService tự động gắn điểm Quality Gate khi tạo sản phẩm."""
        db_mock = AsyncMock()
        task = Task(id=101, title="Phân tích thị trường", workspace_id=1)
        
        service = WorkProductService(db_mock)
        wp = await service.create_from_execution(
            task=task,
            agent_key="marketing",
            raw_content=(
                "Phân tích thị trường cho thấy 50% người dùng cần tính năng này. "
                "Báo cáo số liệu quý 2 đạt 90 điểm. "
                "Hành động đề xuất: Hoàn thiện thông điệp quảng cáo."
            ),
        )

        assert wp.metadata_jsonb is not None
        assert "quality_gate" in wp.metadata_jsonb
        assert wp.metadata_jsonb["quality_gate"]["passed"] is True
