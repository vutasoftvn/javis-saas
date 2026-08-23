# agentos/tools/clusters/strategy_tools.py
from __future__ import annotations

from typing import Any, Optional
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.tools.encore_client import EncoreClient
from agentos.tools.spec import ToolSpecV2


def get_strategy_tools(client: Optional[EncoreClient] = None) -> list[ToolSpecV2]:
    """Tool cluster cho `services/operations/strategy` (Strategy Domain, Phase 2).

    Field mapping khớp đúng DTO thật của từng handler TS (`services/operations/strategy/handlers/*.ts`
    và `services/operations/handlers/project.handler.ts`) — xác nhận bằng cách gọi thật qua
    `encore run` + Postgres thật (roadmap Phase 11b, rà soát 2026-08-23), không suy đoán field name.
    """
    client = client or EncoreClient()

    async def project_get(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy thông tin chi tiết Strategy Project / Venture."""
        project_id = args.get("id") or args.get("projectId")
        return await client.get(f"/operations/projects/{project_id}")

    async def stage_policy_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách Stage Policy đã cấu hình — cần để biết `stagePolicyId` hợp lệ
        trước khi gọi `strategy.gate_evaluation.create` (backend yêu cầu id, không phải
        tên stage dạng chuỗi)."""
        return await client.get("/operations/strategy/stage-policies", params=args)

    async def gate_evaluation_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách Gate Evaluations của project."""
        return await client.get("/operations/strategy/gate-evaluations", params=args)

    async def gate_evaluation_create(args: dict[str, Any]) -> dict[str, Any]:
        """Chạy đánh giá Gate Evaluation theo Stage Policy đã cấu hình (tính điểm/kết quả
        tất định phía backend từ evidence hiện có — không nhận `passed`/`score` từ agent)."""
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
        """Ghi nhận bằng chứng thực tế từ thử nghiệm hoặc phỏng vấn (Evidence) — backend
        tự tính `strength`/`confidence` tất định từ `sourceType`/`rawStrength`/`rawConfidence`/
        `sampleSize`, agent không tự gán điểm."""
        return await client.post("/operations/strategy/evidence", json=args)

    async def evidence_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách bằng chứng (Evidence)."""
        return await client.get("/operations/strategy/evidence", params=args)

    async def decision_record_create(args: dict[str, Any]) -> dict[str, Any]:
        """Ghi nhận quyết định chiến lược (Decision Record: proceed/pivot/kill/hold)."""
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
            name="strategy.stage_policy.list",
            version="1.0.0",
            description="Lấy danh sách Stage Policy (kèm stagePolicyId hợp lệ dùng cho gate_evaluation.create)",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "companyId": {"type": ["string", "number"]},
                    "stageKey": {"type": "string"},
                },
            },
            output_schema={"type": "object"},
            handler=stage_policy_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["strategy", "stage_policy"],
        ),
        ToolSpecV2(
            name="strategy.gate_evaluation.list",
            version="1.0.0",
            description="Lấy danh sách Gate Evaluations của project",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "companyId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
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
            description="Chạy đánh giá Gate Evaluation theo Stage Policy đã cấu hình",
            input_schema={
                "type": "object",
                "properties": {
                    "companyId": {"type": ["string", "number"]},
                    "workspaceId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                    "stagePolicyId": {"type": ["string", "number"]},
                    "blockingRisks": {"type": "array", "items": {"type": "object"}},
                    "humanOverride": {"type": "boolean"},
                },
                "required": ["companyId", "workspaceId", "projectId", "stagePolicyId"],
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
                    "companyId": {"type": ["string", "number"]},
                    "workspaceId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                    "statement": {"type": "string"},
                    "importance": {"type": "number", "description": "1-10, mức độ quan trọng nếu giả định sai"},
                    "uncertainty": {"type": "number", "description": "1-10, mức độ chưa chắc chắn"},
                    "status": {"type": "string"},
                },
                "required": ["companyId", "workspaceId", "projectId", "statement"],
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
                    "workspaceId": {"type": ["string", "number"]},
                    "companyId": {"type": ["string", "number"]},
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
                    "companyId": {"type": ["string", "number"]},
                    "workspaceId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                    "assumptionId": {"type": ["string", "number"]},
                    "hypothesis": {"type": "string"},
                    "method": {"type": "string"},
                    "successCriteria": {"type": "string"},
                    "budget": {"type": "number"},
                    "ownerWorkforceMemberId": {"type": ["string", "number"]},
                    "status": {"type": "string"},
                },
                "required": ["companyId", "workspaceId", "projectId", "hypothesis", "method", "successCriteria"],
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
                    "companyId": {"type": ["string", "number"]},
                    "workspaceId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                    "experimentId": {"type": ["string", "number"]},
                    "sourceType": {
                        "type": "string",
                        "description": "financial_transaction | customer_interview | prototype_test | experiment_metric | survey | 3rd_party_data | observation",
                    },
                    "claim": {"type": "string"},
                    "rawStrength": {"type": "number", "description": "0.0-1.0 nếu có"},
                    "rawConfidence": {"type": "number", "description": "0.0-1.0 nếu có"},
                    "sampleSize": {"type": "number"},
                    "supportsOrRefutes": {"type": "string", "enum": ["supports", "refutes", "neutral"]},
                },
                "required": ["companyId", "workspaceId", "projectId", "sourceType", "claim"],
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
                    "workspaceId": {"type": ["string", "number"]},
                    "companyId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                    "experimentId": {"type": ["string", "number"]},
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
            description="Ghi nhận quyết định chiến lược (Decision Record: proceed/pivot/kill/hold)",
            input_schema={
                "type": "object",
                "properties": {
                    "companyId": {"type": ["string", "number"]},
                    "workspaceId": {"type": ["string", "number"]},
                    "projectId": {"type": ["string", "number"]},
                    "gateEvaluationId": {"type": ["string", "number"]},
                    "decision": {"type": "string", "enum": ["proceed", "pivot", "kill", "hold"]},
                    "actorWorkforceMemberId": {"type": ["string", "number"]},
                    "notes": {"type": "string"},
                },
                "required": ["companyId", "workspaceId", "projectId", "decision"],
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
