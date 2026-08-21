import hmac
import hashlib
import json
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from workforce.automation.models import AutomationRun, AutomationCallback, AutomationDefinition


def generate_hmac_signature(payload_bytes: bytes, secret_key: str) -> str:
    """Tạo chữ ký HMAC-SHA256 cho payload."""
    signature = hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def verify_hmac_signature(payload_bytes: bytes, signature_header: str, secret_key: str) -> bool:
    """Xác thực chữ ký HMAC-SHA256 từ header."""
    if not signature_header or not secret_key:
        return False
    expected = generate_hmac_signature(payload_bytes, secret_key)
    return hmac.compare_digest(expected, signature_header.strip())


async def dispatch_n8n_workflow(
    db: Session,
    workspace_id: int,
    automation_key: str,
    payload: Dict[str, Any],
    webhook_url: Optional[str] = None,
    secret_key: str = "cosa-n8n-default-secret",
) -> Dict[str, Any]:
    """Kích hoạt chạy một workflow n8n và khởi tạo AutomationRun."""
    run_id = generate_snowflake_id()
    idempotency_key = f"n8n-run-{run_id}"

    # Check AutomationDefinition governance rules
    definition = (
        db.query(AutomationDefinition)
        .filter(AutomationDefinition.automation_key == automation_key)
        .first()
    )
    risk_level = definition.risk_level if definition else "low"
    if definition and definition.approval_mode != "none":
        # Check if an active approval exists or pause dispatch
        from workforce.agents.governance.models import AgentApproval
        approval = (
            db.query(AgentApproval)
            .filter(
                AgentApproval.workspace_id == workspace_id,
                AgentApproval.tool_name == automation_key,
                AgentApproval.status == "approved",
            )
            .order_by(AgentApproval.requested_at.desc())
            .first()
        )
        if not approval:
            # Create an approval request instead of dispatching
            from workforce.agents.governance.approval_service import ApprovalService
            appr = ApprovalService.create_approval(
                db=db,
                workspace_id=workspace_id,
                company_id=workspace_id,
                agent_key="n8n_gateway",
                action_type="automation_execution",
                tool_name=automation_key,
                input_preview=payload,
                risk_level=risk_level,
            )
            return {
                "status": "approval_required",
                "run_id": str(run_id),
                "approval_id": str(appr.id),
                "automation_key": automation_key,
                "reason": f"Automation {automation_key} requires approval before execution",
            }

    auto_run = AutomationRun(
        id=run_id,
        workspace_id=workspace_id,
        automation_key=automation_key,
        provider="n8n",
        status="running",
        risk_level=risk_level,
        idempotency_key=idempotency_key,
        payload_jsonb=payload,
        started_at=datetime.now(timezone.utc),
    )
    db.add(auto_run)
    db.commit()
    db.refresh(auto_run)

    # Nếu có webhook_url, gửi HTTP POST kèm signature
    if webhook_url:
        payload_with_meta = {
            "run_id": str(run_id),
            "workspace_id": str(workspace_id),
            "automation_key": automation_key,
            "data": payload,
        }
        body_bytes = json.dumps(payload_with_meta).encode("utf-8")
        signature = generate_hmac_signature(body_bytes, secret_key)

        headers = {
            "Content-Type": "application/json",
            "X-COSA-Signature": signature,
            "X-COSA-Run-ID": str(run_id),
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook_url, content=body_bytes, headers=headers)
                if resp.status_code in (200, 201, 202):
                    auto_run.provider_execution_id = resp.json().get("executionId")
                    db.add(auto_run)
                    db.commit()
        except Exception as e:
            auto_run.status = "failed"
            auto_run.error_summary = str(e)
            db.add(auto_run)
            db.commit()

    return {
        "status": "dispatched",
        "run_id": str(run_id),
        "automation_key": automation_key,
        "run_status": auto_run.status,
    }


def handle_n8n_callback(
    db: Session,
    run_id: int,
    payload: Dict[str, Any],
    raw_body_bytes: bytes,
    signature_header: str,
    secret_key: str = "cosa-n8n-default-secret",
) -> Dict[str, Any]:
    """Xử lý webhook callback từ n8n khi workflow hoàn thành."""
    # 1. Xác thực chữ ký HMAC
    is_valid = verify_hmac_signature(raw_body_bytes, signature_header, secret_key)

    # 2. Tìm AutomationRun
    auto_run = db.query(AutomationRun).filter(AutomationRun.id == run_id).first()
    if not auto_run:
        raise ValueError(f"AutomationRun {run_id} không tồn tại")

    callback_id = generate_snowflake_id()
    callback = AutomationCallback(
        id=callback_id,
        run_id=run_id,
        provider_execution_id=payload.get("provider_execution_id", "n8n-exec"),
        status=payload.get("status", "succeeded"),
        signature=signature_header,
        verified=is_valid,
        payload_jsonb=payload,
        received_at=datetime.now(timezone.utc),
    )
    db.add(callback)

    if not is_valid:
        auto_run.status = "failed"
        auto_run.error_code = "INVALID_SIGNATURE"
        auto_run.error_summary = "Chữ ký HMAC không khớp với khóa bí mật"
        db.add(auto_run)
        db.commit()
        raise PermissionError("Chữ ký HMAC không hợp lệ")

    # 3. Cập nhật kết quả thành công
    status_str = payload.get("status", "succeeded")
    auto_run.status = status_str
    auto_run.result_jsonb = payload.get("result", {})
    auto_run.finished_at = datetime.now(timezone.utc)
    if status_str == "failed":
        auto_run.error_summary = payload.get("error")

    db.add(auto_run)
    db.commit()

    return {
        "status": "success",
        "run_id": str(run_id),
        "run_status": auto_run.status,
        "verified": True,
    }
