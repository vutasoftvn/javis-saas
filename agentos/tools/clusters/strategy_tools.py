# agentos/tools/clusters/strategy_tools.py
from __future__ import annotations

from typing import Any, Optional
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.tools.encore_client import EncoreClient
from agentos.tools.spec import ToolSpecV2


def get_strategy_tools(client: Optional[EncoreClient] = None) -> list[ToolSpecV2]:
    client = client or EncoreClient()

    async def project_get(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy thông tin chi tiết Strategy Project / Venture."""
        project_id = args.get("id") or args.get("projectId")
        return await client.get(f"/operations/strategy/projects/{project_id}")

    async def gate_evaluation_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách Gate Evaluations của project."""
        return await client.get("/operations/strategy/gate-evaluations", params=args)

    async def gate_evaluation_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo đánh giá Gate Evaluation theo stage transition policy."""
        return await client.post("/operations/strategy/gate-evaluations", json=args)

    async def assumption_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo mới giả định chiến lược (Assumption)."""
        return await client.post("/operations/strategy/assumptions", json=args)

    async def assumption_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách giả định chiến lược (Assumptions)."""
        return await client.get("/operations/strategy/assumptions", params=args)

    async def experiment_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo mới thử nghiệm kiểm chứng giả định (Experiment)."""
        return await client.post("/operations/strategy/experiments", json=args)

    async def evidence_create(args: dict[str, Any]) -> dict[str, Any]:
        """Ghi nhận bằng chứng thực tế từ thử nghiệm hoặc phỏng vấn (Evidence)."""
        return await client.post("/operations/strategy/evidence", json=args)

    async def evidence_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách bằng chứng (Evidence)."""
        return await client.get("/operations/strategy/evidence", params=args)

    async def decision_record_create(args: dict[str, Any]) -> dict[str, Any]:
        """Ghi nhận quyết định chiến lược (Decision Record / Pivot)."""
        return await client.post("/operations/strategy/decision-records", json=args)

    async def next_best_action_get(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách Next Best Actions được xếp hạng tất định theo thuật toán Strategy Domain."""
        project_id = args.get("id") or args.get("projectId")
        return await client.get(f"/operations/strategy/projects/{project_id}/next-best-actions")

    return [
        ToolSpecV2(
            name="strategy.project.get",
            version="1.0.0",
            description="Lấy thông tin chi tiết Strategy Project / Venture",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                },
            },
            output_schema={"type": "object"},
            handler=project_get,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["strategy", "project"],
        ),
        ToolSpecV2(
            name="strategy.gate_evaluation.list",
            version="1.0.0",
            description="Lấy danh sách Gate Evaluations của project",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "stage": {"type": "string"},
                },
            },
            output_schema={"type": "object"},
            handler=gate_evaluation_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["strategy", "gate_evaluation"],
        ),
        ToolSpecV2(
            name="strategy.gate_evaluation.create",
            version="1.0.0",
            description="Tạo đánh giá Gate Evaluation theo stage policy",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "currentStage": {"type": "string"},
                    "targetStage": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "score": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["projectId", "currentStage", "targetStage"],
            },
            output_schema={"type": "object"},
            handler=gate_evaluation_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["strategy", "gate_evaluation"],
        ),
        ToolSpecV2(
            name="strategy.assumption.create",
            version="1.0.0",
            description="Tạo mới giả định chiến lược (Assumption)",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "criticality": {"type": "number"},
                    "status": {"type": "string"},
                },
                "required": ["projectId", "title"],
            },
            output_schema={"type": "object"},
            handler=assumption_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["strategy", "assumption"],
        ),
        ToolSpecV2(
            name="strategy.assumption.list",
            version="1.0.0",
            description="Lấy danh sách giả định chiến lược (Assumptions)",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "status": {"type": "string"},
                },
            },
            output_schema={"type": "object"},
            handler=assumption_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["strategy", "assumption"],
        ),
        ToolSpecV2(
            name="strategy.experiment.create",
            version="1.0.0",
            description="Tạo mới thử nghiệm kiểm chứng giả định (Experiment)",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "assumptionId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "type": {"type": "string"},
                    "metric": {"type": "string"},
                    "criteria": {"type": "string"},
                },
                "required": ["projectId", "title"],
            },
            output_schema={"type": "object"},
            handler=experiment_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["strategy", "experiment"],
        ),
        ToolSpecV2(
            name="strategy.evidence.create",
            version="1.0.0",
            description="Ghi nhận bằng chứng thực tế từ thử nghiệm hoặc phỏng vấn (Evidence)",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "experimentId": {"type": ["string", "number"]},
                    "assumptionId": {"type": ["string", "number"]},
                    "type": {"type": "string"},
                    "strength": {"type": "string"},
                    "summary": {"type": "string"},
                    "data": {"type": "object"},
                },
                "required": ["projectId", "summary"],
            },
            output_schema={"type": "object"},
            handler=evidence_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["strategy", "evidence"],
        ),
        ToolSpecV2(
            name="strategy.evidence.list",
            version="1.0.0",
            description="Lấy danh sách bằng chứng (Evidence)",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "assumptionId": {"type": ["string", "number"]},
                },
            },
            output_schema={"type": "object"},
            handler=evidence_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["strategy", "evidence"],
        ),
        ToolSpecV2(
            name="strategy.decision_record.create",
            version="1.0.0",
            description="Ghi nhận quyết định chiến lược (Decision Record / Pivot)",
            input_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": ["string", "number"]},
                    "decisionType": {"type": "string"},
                    "title": {"type": "string"},
                    "rationale": {"type": "string"},
                    "evidenceIds": {"type": "array", "items": {"type": ["string", "number"]}},
                },
                "required": ["projectId", "title", "rationale"],
            },
            output_schema={"type": "object"},
            handler=decision_record_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["strategy", "decision_record"],
        ),
        ToolSpecV2(
            name="strategy.next_best_action.get",
            version="1.0.0",
            description="Lấy danh sách Next Best Actions được xếp hạng tất định theo thuật toán Strategy Domain",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                },
            },
            output_schema={"type": "object"},
            handler=next_best_action_get,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["strategy", "next_best_action"],
        ),
    ]
