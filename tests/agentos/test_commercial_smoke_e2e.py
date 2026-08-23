from __future__ import annotations

from typing import Any
import pytest

from agentos.core.policy import PermissionLevel, PolicyEngine
from agentos.tools.clusters.commercial_tools import get_commercial_tools
from agentos.tools.clusters.strategy_tools import get_strategy_tools
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry


class _MockCrossDomainBackend:
    """In-memory backend simulating both Strategy and Commercial services."""

    def __init__(self) -> None:
        self.leads: dict[str, dict[str, Any]] = {}
        self.opportunities: dict[str, dict[str, Any]] = {}
        self.experiments: dict[str, dict[str, Any]] = {}
        self.evidence: dict[str, dict[str, Any]] = {}

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if path == "/commercial/leads":
            return {"items": list(self.leads.values())}
        elif path == "/commercial/opportunities":
            return {"items": list(self.opportunities.values())}
        elif path == "/operations/strategy/experiments":
            return {"items": list(self.experiments.values())}
        elif path == "/operations/strategy/evidence":
            return {"items": list(self.evidence.values())}
        return {"items": []}

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(json or {})
        if path == "/commercial/leads":
            lead_id = f"lead_{len(self.leads) + 1}"
            data["id"] = lead_id
            self.leads[lead_id] = data
            return data
        elif path.startswith("/commercial/leads/") and "/stage" in path:
            lead_id = path.split("/")[3]
            if lead_id in self.leads:
                self.leads[lead_id]["stage"] = data.get("stage")
            return {"id": lead_id, "status": "updated", **data}
        elif path == "/commercial/opportunities":
            opp_id = f"opp_{len(self.opportunities) + 1}"
            data["id"] = opp_id
            self.opportunities[opp_id] = data
            return data
        elif path.startswith("/commercial/opportunities/") and "/stage" in path:
            opp_id = path.split("/")[3]
            if opp_id in self.opportunities:
                self.opportunities[opp_id]["stage"] = data.get("stage")
            return {"id": opp_id, "status": "updated", **data}
        elif path == "/operations/strategy/experiments":
            exp_id = f"exp_{len(self.experiments) + 1}"
            data["id"] = exp_id
            self.experiments[exp_id] = data
            return data
        elif path == "/operations/strategy/evidence":
            evi_id = f"evi_{len(self.evidence) + 1}"
            data["id"] = evi_id
            self.evidence[evi_id] = data
            return data
        return {"status": "ok", **data}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_commercial_and_strategy_cross_domain_linkage_smoke():
    backend = _MockCrossDomainBackend()
    client = EncoreClient()
    client.get = backend.get
    client.post = backend.post

    registry = ToolRegistry()
    for tool in get_commercial_tools(client):
        registry.register(tool)
    for tool in get_strategy_tools(client):
        registry.register(tool)

    # -------------------------------------------------------------------------
    # 1. Tạo 1 Lead qua commercial.lead.create
    # -------------------------------------------------------------------------
    lead_res = await registry.invoke(
        "commercial.lead.create",
        {
            "workspaceId": "ws_marketing",
            "name": "Acme Marketing Agency",
            "email": "contact@acmeagency.com",
            "company": "Acme Corp",
        },
    )
    assert lead_res.get("id") is not None, "Failed to create Lead via commercial.lead.create"
    lead_id = lead_res["id"]
    assert lead_id in backend.leads

    # -------------------------------------------------------------------------
    # 2. Tạo Experiment với field tham chiếu trỏ tới Lead vừa tạo (nguyên tắc §4.5)
    # -------------------------------------------------------------------------
    # NOTE (rà soát 2026-08-23): bảng `experiments` thật (`services/operations/strategy`)
    # KHÔNG có cột `sourceExperimentId`/`leadRef` như roadmap §4.5 giả định — field này chỉ
    # được mock backend ở đây echo lại, sẽ bị Encore thật bỏ qua âm thầm nếu gọi thật. Đây là
    # gap thật cần 1 quyết định thiết kế riêng (thêm cột tham chiếu vào schema thật), không
    # phải lỗi field-mapping đơn thuần của `strategy_tools.py` — không tự ý thêm cột khi chưa
    # xác nhận.
    exp_res = await registry.invoke(
        "strategy.experiment.create",
        {
            "companyId": "company_growth_1",
            "workspaceId": "ws_marketing",
            "projectId": "proj_growth_1",
            "hypothesis": "Cold outreach to Agency Leads converts to positive replies",
            "method": "outreach_campaign",
            "successCriteria": ">= 20% positive reply rate",
            "sourceExperimentId": lead_id,  # xem NOTE ở trên — không tồn tại ở schema thật
        },
    )
    assert exp_res.get("id") is not None, "Failed to create Experiment linked to Lead"
    exp_id = exp_res["id"]
    assert backend.experiments[exp_id]["sourceExperimentId"] == lead_id

    # -------------------------------------------------------------------------
    # 3. Ghi Evidence với source_type trỏ về Lead/Opportunity
    # -------------------------------------------------------------------------
    evidence_res = await registry.invoke(
        "strategy.evidence.create",
        {
            "companyId": "company_growth_1",
            "workspaceId": "ws_marketing",
            "projectId": "proj_growth_1",
            "experimentId": exp_id,
            "sourceType": "customer_interview",
            "claim": "Acme CEO replied enthusiastically: interested in pilot immediately.",
            "data": {
                "source_type": "lead",
                "source_id": lead_id,
                "sentiment": "positive",
                "budget_confirmed": True,
            },
        },
    )
    assert evidence_res.get("id") is not None, "Failed to record Evidence"
    evi_id = evidence_res["id"]
    assert backend.evidence[evi_id]["data"]["source_id"] == lead_id

    # -------------------------------------------------------------------------
    # 4. Tạo Sales Opportunity cho Lead và cập nhật stage dựa trên Evidence
    # -------------------------------------------------------------------------
    opp_res = await registry.invoke(
        "commercial.opportunity.create",
        {
            "workspaceId": "ws_marketing",
            "name": "Acme Agency Enterprise Deal",
            "leadId": lead_id,
            "amount": 25000,
            "stage": "qualified",
        },
    )
    assert opp_res.get("id") is not None, "Failed to create Opportunity"
    opp_id = opp_res["id"]

    # Cập nhật Opportunity stage dựa trên bằng chứng kiểm chứng thành công
    stage_update_res = await registry.invoke(
        "commercial.opportunity.update_stage",
        {"id": opp_id, "stage": "proposal"},
    )
    assert stage_update_res.get("status") == "updated"
    assert backend.opportunities[opp_id]["stage"] == "proposal"

    # -------------------------------------------------------------------------
    # 5. Assert tính nhân quả 2 chiều: Lead <-> Experiment <-> Evidence <-> Opportunity
    # -------------------------------------------------------------------------
    # Lead -> Experiment query
    matching_experiments = [e for e in backend.experiments.values() if e.get("sourceExperimentId") == lead_id]
    assert len(matching_experiments) == 1, "Failed to resolve Experiment from Lead reference."

    # Experiment -> Evidence query
    matching_evidence = [ev for ev in backend.evidence.values() if ev.get("experimentId") == exp_id]
    assert len(matching_evidence) == 1, "Failed to resolve Evidence from Experiment."
    assert matching_evidence[0]["data"]["source_id"] == lead_id

    # Lead -> Opportunity query
    matching_opps = [op for op in backend.opportunities.values() if op.get("leadId") == lead_id]
    assert len(matching_opps) == 1, "Failed to resolve Opportunity from Lead."
    assert matching_opps[0]["stage"] == "proposal"
