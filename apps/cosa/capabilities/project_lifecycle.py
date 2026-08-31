from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "ANALYTICS_METRIC_CONTRACT_GET_SPEC",
    "ANALYTICS_PMF_SCOREBOARD_GET_SPEC",
    "ANALYTICS_PMF_SCOREBOARD_PROPOSE_SPEC",
    "STRATEGY_EVIDENCE_CREATE_SPEC",
    "STRATEGY_EVIDENCE_LIST_SPEC",
    "STRATEGY_GATE_EVALUATION_CREATE_SPEC",
    "STRATEGY_NEXT_BEST_ACTION_GET_SPEC",
    "STRATEGY_PILOT_CREATE_DRAFT_SPEC",
    "STRATEGY_PILOT_GET_SPEC",
    "STRATEGY_PROJECT_GET_SPEC",
    "create_analytics_metric_contract_get_handler",
    "create_analytics_pmf_scoreboard_get_handler",
    "create_analytics_pmf_scoreboard_propose_handler",
    "create_strategy_evidence_create_handler",
    "create_strategy_evidence_list_handler",
    "create_strategy_gate_evaluation_create_handler",
    "create_strategy_next_best_action_get_handler",
    "create_strategy_pilot_create_draft_handler",
    "create_strategy_pilot_get_handler",
    "create_strategy_project_get_handler",
]


def _extract_workspace_id(payload: dict[str, Any], context: Any = None) -> str:
    ctx_ws_id = None
    if context is not None:
        if isinstance(context, dict):
            ctx_ws_id = context.get("workspace_id")
        else:
            ctx_ws_id = getattr(context, "workspace_id", None)

    payload_ws_id = payload.get("workspace_id")

    if ctx_ws_id and payload_ws_id and str(ctx_ws_id) != str(payload_ws_id):
        raise ValueError(
            f"Cross-tenant workspace_id mismatch: context='{ctx_ws_id}', payload='{payload_ws_id}'"
        )

    ws_id = ctx_ws_id or payload_ws_id
    if not ws_id:
        raise ValueError("workspace_id is required")
    return str(ws_id)


STRATEGY_PROJECT_GET_SPEC = CapabilitySpec(
    id="strategy.project.get",
    description="Lấy thông tin lifecycle stage và context của dự án trong workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "project": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_EVIDENCE_LIST_SPEC = CapabilitySpec(
    id="strategy.evidence.list",
    description="Liệt kê bằng chứng (evidence) đã thu thập của dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "experiment_id": {"type": ["string", "integer"]},
            "status": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "items": {"type": "array"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_EVIDENCE_CREATE_SPEC = CapabilitySpec(
    id="strategy.evidence.create",
    description="Đề xuất bản ghi bằng chứng mới (candidate evidence) cho dự án để founder review.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id", "source_type", "claim"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "experiment_id": {"type": ["string", "integer"]},
            "source_type": {"type": "string"},
            "claim": {"type": "string"},
            "sample_size": {"type": "integer"},
            "raw_strength": {"type": "number"},
            "raw_confidence": {"type": "number"},
            "supports_or_refutes": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "evidence": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_GATE_EVALUATION_CREATE_SPEC = CapabilitySpec(
    id="strategy.gate_evaluation.create",
    description="Thực hiện đánh giá gate khuyến nghị (recommendation-only) theo stage policy của dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id", "stage_policy_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "stage_policy_id": {"type": ["string", "integer"]},
            "blocking_risks": {"type": "array"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "evaluation": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_NEXT_BEST_ACTION_GET_SPEC = CapabilitySpec(
    id="strategy.next_best_action.get",
    description="Lấy danh sách các hành động tối ưu tiếp theo (Next Best Actions) cho dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "actions": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_PILOT_GET_SPEC = CapabilitySpec(
    id="strategy.pilot.get",
    description="Lấy thông tin và trạng thái của Pilot Run trong workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "pilot_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "pilot": {"type": "object"},
            "items": {"type": "array"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_PILOT_CREATE_DRAFT_SPEC = CapabilitySpec(
    id="strategy.pilot.create_draft",
    description="Đề xuất tạo bản nháp Pilot Run (Draft) cho dự án. Yêu cầu Founder phê duyệt.",
    risk=CapabilityRisk.MEDIUM,
    input_schema={
        "type": "object",
        "required": [
            "project_id",
            "design_partner_evidence_refs",
            "metric_contract_artifact_ref",
            "instrumentation_artifact_ref",
            "onboarding_artifact_ref",
            "rollback_artifact_ref",
            "release_owner_member_id",
        ],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "experiment_id": {"type": ["string", "integer"]},
            "design_partner_evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
            },
            "metric_contract_artifact_ref": {"type": "string"},
            "instrumentation_artifact_ref": {"type": "string"},
            "onboarding_artifact_ref": {"type": "string"},
            "support_escalation_artifact_ref": {"type": "string"},
            "rollback_artifact_ref": {"type": "string"},
            "release_owner_member_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "pilot": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_strategy_project_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        project_id = str(payload["project_id"])

        res = await client.get(
            "/operations/strategy/stage-context",
            params={"projectId": project_id},
            headers=headers,
        )

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Thông tin stage context cho project {project_id}.",
            sources=[{"source": f"project:{project_id}"}],
            confidence=1.0,
            next_actions=["Xem xét bằng chứng và các yêu cầu gate của giai đoạn hiện tại"],
        )

        return {"project": res, "advisory": advisory}

    return handler


def create_strategy_evidence_list_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        params: dict[str, Any] = {"projectId": str(payload["project_id"])}

        if payload.get("experiment_id"):
            params["experimentId"] = str(payload["experiment_id"])
        if payload.get("status"):
            params["status"] = str(payload["status"])

        res = await client.get("/operations/strategy/evidence", params=params, headers=headers)
        items = res.get("items", []) if isinstance(res, dict) else []

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Đã tìm thấy {len(items)} bằng chứng cho project {payload['project_id']}.",
            sources=[{"source": f"evidence_list:{payload['project_id']}"}],
            confidence=1.0,
            next_actions=[],
        )

        return {"items": items, "advisory": advisory}

    return handler


def create_strategy_evidence_create_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        post_body = {
            "projectId": str(payload["project_id"]),
            "sourceType": payload["source_type"],
            "claim": payload["claim"],
            "status": "candidate",  # Agents can only propose candidate evidence
        }
        if payload.get("experiment_id"):
            post_body["experimentId"] = str(payload["experiment_id"])
        if "sample_size" in payload and payload["sample_size"] is not None:
            post_body["sampleSize"] = payload["sample_size"]
        if "raw_strength" in payload and payload["raw_strength"] is not None:
            post_body["rawStrength"] = payload["raw_strength"]
        if "raw_confidence" in payload and payload["raw_confidence"] is not None:
            post_body["rawConfidence"] = payload["raw_confidence"]
        if payload.get("supports_or_refutes"):
            post_body["supportsOrRefutes"] = payload["supports_or_refutes"]

        res = await client.post("/operations/strategy/evidence", json=post_body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đã tạo candidate evidence cho project {payload['project_id']}: '{payload['claim']}'. Đang chờ founder phê duyệt.",
            sources=[{"source": f"evidence:{res.get('id', '')}"}],
            confidence=0.95,
            next_actions=[
                "Founder xem xét và phê duyệt candidate evidence trước khi đánh giá gate"
            ],
        )

        return {"evidence": res, "advisory": advisory}

    return handler


def create_strategy_gate_evaluation_create_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        post_body = {
            "projectId": str(payload["project_id"]),
            "stagePolicyId": str(payload["stage_policy_id"]),
            "blockingRisks": payload.get("blocking_risks", []),
        }

        res = await client.post(
            "/operations/strategy/gate-evaluations",
            json=post_body,
            headers=headers,
        )

        result_status = res.get("result", "pending")
        req_met = res.get("requirementsMet", False)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=(
                f"Đánh giá gate khuyến nghị cho project {payload['project_id']}: "
                f"Kết quả: {result_status}, Yêu cầu đạt: {req_met}. "
                "Lưu ý: Đánh giá gate chỉ mang tính khuyến nghị, không tự động chuyển giai đoạn."
            ),
            sources=[{"source": f"gate_eval:{res.get('id', '')}"}],
            confidence=1.0,
            next_actions=["Chuyển giai đoạn chính thức qua endpoint transition nếu đạt điều kiện"],
        )

        return {"evaluation": res, "advisory": advisory}

    return handler


def create_strategy_next_best_action_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        project_id = str(payload["project_id"])

        res = await client.get(
            f"/operations/strategy/projects/{project_id}/next-best-actions",
            headers=headers,
        )

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Đã truy vấn Next Best Actions cho project {project_id}.",
            sources=[{"source": f"project_nba:{project_id}"}],
            confidence=1.0,
            next_actions=[],
        )

        return {"actions": res, "advisory": advisory}

    return handler


def create_strategy_pilot_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        if payload.get("pilot_id"):
            pilot_id = str(payload["pilot_id"])
            res = await client.get(f"/operations/strategy/pilots/{pilot_id}", headers=headers)
            advisory = wrap_advisory(
                layer="CURRENT_LAW",
                label="insight",
                content=f"Thông tin Pilot Run {pilot_id} (Status: {res.get('status', 'unknown')}).",
                sources=[{"source": f"pilot_run:{pilot_id}"}],
                confidence=1.0,
                next_actions=[],
            )
            return {"pilot": res, "advisory": advisory}

        params: dict[str, Any] = {}
        if payload.get("project_id"):
            params["projectId"] = str(payload["project_id"])

        res = await client.get("/operations/strategy/pilots", params=params, headers=headers)
        items = res.get("items", []) if isinstance(res, dict) else []

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Đã tìm thấy {len(items)} pilot runs trong workspace.",
            sources=[{"source": "pilot_runs_list"}],
            confidence=1.0,
            next_actions=[],
        )

        return {"items": items, "advisory": advisory}

    return handler


def create_strategy_pilot_create_draft_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        post_body = {
            "projectId": str(payload["project_id"]),
            "designPartnerEvidenceRefs": [str(r) for r in payload["design_partner_evidence_refs"]],
            "metricContractArtifactRef": str(payload["metric_contract_artifact_ref"]),
            "instrumentationArtifactRef": str(payload["instrumentation_artifact_ref"]),
            "onboardingArtifactRef": str(payload["onboarding_artifact_ref"]),
            "rollbackArtifactRef": str(payload["rollback_artifact_ref"]),
            "releaseOwnerMemberId": str(payload["release_owner_member_id"]),
        }
        if payload.get("experiment_id"):
            post_body["experimentId"] = str(payload["experiment_id"])
        if payload.get("support_escalation_artifact_ref"):
            post_body["supportEscalationArtifactRef"] = str(
                payload["support_escalation_artifact_ref"]
            )

        res = await client.post("/operations/strategy/pilots", json=post_body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=(
                f"Đã tạo bản nháp Pilot Run (Draft ID: {res.get('id', '')}) cho project {payload['project_id']}. "
                "Cần Founder/Admin xem xét và phê duyệt (Human Authorization) trước khi kích hoạt."
            ),
            sources=[{"source": f"pilot_run:{res.get('id', '')}"}],
            confidence=1.0,
            next_actions=[
                "Founder duyệt Pilot Run qua endpoint /operations/strategy/pilots/:id/approve"
            ],
        )

        return {"pilot": res, "advisory": advisory}

    return handler


ANALYTICS_METRIC_CONTRACT_GET_SPEC = CapabilitySpec(
    id="analytics.metric_contract.get",
    description="Lấy thông tin định nghĩa metric contract và trạng thái version trong workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "contract_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "contracts": {"type": "array"},
            "contract": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

ANALYTICS_PMF_SCOREBOARD_GET_SPEC = CapabilitySpec(
    id="analytics.pmf_scoreboard.get",
    description="Lấy kết quả tính toán PMF scoreboard và các thành phần dữ liệu của dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "run_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "runs": {"type": "array"},
            "run": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

ANALYTICS_PMF_SCOREBOARD_PROPOSE_SPEC = CapabilitySpec(
    id="analytics.pmf_scoreboard.propose",
    description="Đề xuất bản ghi tổng hợp PMF advisory memo (ACTION / DECISION / LEARN) dựa trên các run đã tính toán trong Company Services.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "classification": {"type": "string"},
            "memo": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_analytics_metric_contract_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        if payload.get("contract_id"):
            contract_id = str(payload["contract_id"])
            res = await client.get(
                f"/operations/strategy/metric-contracts/{contract_id}", headers=headers
            )
            advisory = wrap_advisory(
                layer="CURRENT_LAW",
                label="insight",
                content=f"Thông tin Metric Contract {contract_id}.",
                sources=[{"source": f"metric_contract:{contract_id}"}],
                confidence=1.0,
                next_actions=[],
            )
            return {"contract": res, "advisory": advisory}

        params: dict[str, Any] = {}
        if payload.get("project_id"):
            params["projectId"] = str(payload["project_id"])

        res = await client.get(
            "/operations/strategy/metric-contracts", params=params, headers=headers
        )
        items = res.get("items", []) if isinstance(res, dict) else []

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Tìm thấy {len(items)} metric contracts trong workspace.",
            sources=[{"source": "metric_contracts_list"}],
            confidence=1.0,
            next_actions=[],
        )

        return {"contracts": items, "items": items, "advisory": advisory}

    return handler


def create_analytics_pmf_scoreboard_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        if payload.get("run_id"):
            run_id = str(payload["run_id"])
            res = await client.get(
                f"/operations/strategy/pmf-scoreboards/{run_id}", headers=headers
            )
            advisory = wrap_advisory(
                layer="CURRENT_LAW",
                label="insight",
                content=f"PMF Scoreboard Run {run_id} (Kết quả: {res.get('result', 'unknown')}).",
                sources=[{"source": f"pmf_run:{run_id}"}],
                confidence=1.0,
                next_actions=[],
            )
            return {"run": res, "advisory": advisory}

        params: dict[str, Any] = {}
        if payload.get("project_id"):
            params["projectId"] = str(payload["project_id"])

        res = await client.get(
            "/operations/strategy/pmf-scoreboards", params=params, headers=headers
        )
        items = res.get("items", []) if isinstance(res, dict) else []

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Tìm thấy {len(items)} PMF scoreboard runs.",
            sources=[{"source": "pmf_scoreboards_list"}],
            confidence=1.0,
            next_actions=[],
        )

        return {"runs": items, "items": items, "advisory": advisory}

    return handler


def create_analytics_pmf_scoreboard_propose_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        project_id = str(payload["project_id"])

        res = await client.get(
            "/operations/strategy/pmf-scoreboards",
            params={"projectId": project_id},
            headers=headers,
        )
        items = res.get("items", []) if isinstance(res, dict) else []

        memo: dict[str, Any]
        if not items:
            classification = "INSUFFICIENT_DATA"
            memo = {
                "action": "Thu thập thêm dữ liệu telemetry từ pilot và chuẩn bị metric contract",
                "decision": "Chưa đủ dữ liệu để đánh giá PMF",
                "learn": "Dự án chưa có PMF scoreboard run nào được tính toán từ dữ liệu thực tế",
                "source_ids": [],
                "human_owner": "Founder / Product DRI",
            }
        else:
            latest_run = items[0]
            classification = latest_run.get("result", "MIXED")
            missing = latest_run.get("missingDataFlags", [])
            reliability = latest_run.get("reliabilityFlags", [])

            if classification == "PROMISING":
                action = "Chuẩn bị tài liệu G4 Gate Review và tổng hợp feedback định tính"
                decision = (
                    "Tín hiệu PMF khả quan (PROMISING) — đề xuất tiếp tục mở rộng cohort thử nghiệm"
                )
            elif classification == "CONCERNING":
                action = "Tổ chức phiên họp Pivot/Persevere để rà soát lại ICP và bài toán cốt lõi"
                decision = (
                    "Tín hiệu PMF có rủi ro (CONCERNING) — không khuyến nghị mở rộng chi tiêu GTM"
                )
            elif classification == "INSUFFICIENT_DATA":
                action = "Bổ sung các snapshot telemetry còn thiếu để hoàn thiện bảng điểm"
                decision = "Dữ liệu chưa hoàn thiện"
            else:
                action = "Phân tích sâu các chỉ số trái chiều giữa retention và phản hồi khách hàng"
                decision = "Kết quả hỗn hợp (MIXED) — cần thêm chu kỳ thử nghiệm"

            memo = {
                "action": action,
                "decision": decision,
                "learn": f"Phân tích từ run ID {latest_run.get('id', '')} (Hash: {latest_run.get('calculationHash', '')[:12]}...). Missing: {missing}, Reliability flags: {reliability}",
                "source_ids": latest_run.get("inputSnapshotIds", []),
                "human_owner": "Founder / Product DRI",
            }

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đề xuất PMF Advisory Memo cho project {project_id}: Phân loại [{classification}].",
            sources=[{"source": f"pmf_proposal:{project_id}"}],
            confidence=0.95,
            next_actions=[memo["action"]],
        )

        return {
            "status": "completed",
            "output_payload": {
                "classification": classification,
                "memo": memo,
            },
            "classification": classification,
            "memo": memo,
            "advisory": advisory,
        }

    return handler
