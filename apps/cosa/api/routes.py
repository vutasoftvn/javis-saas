"""Run operations routes for COSA Agent Platform (minimal post-split)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from apps.cosa.api.event_stream import get_cosa_event_stream_manager
from apps.cosa.api.project_context import require_project_context_match, verify_project_context
from apps.cosa.api.schemas import CancelRunResponse
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane

__all__ = ["create_cosa_router", "router"]

logger = logging.getLogger("cosa.api.routes")

router = APIRouter(prefix="/agent", tags=["agent-chat"])


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection từ `app.state.plane`."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


# 6. POST /agent/runs/{run_id}/cancel
@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_run(
    request: Request,
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    project_id: str | None = Query(None),
):
    plane = get_cosa_plane(request)
    stream_mgr = get_cosa_event_stream_manager()

    owned_run = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    if owned_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Project-scoped Founder Hub — resolve Project TỪ CHÍNH run đã lưu (không
    # bắt client tự khai lại project_id trên mỗi request cancel/events — run
    # đã gắn cố định 1 project từ lúc tạo) rồi verify qua Company, thay vì chỉ
    # tin workspace_id như trước Task 2. Run legacy (project_id=None, trước
    # Task 2) vẫn cancel được bằng workspace scope như cũ — không hồi tố yêu
    # cầu Project lên dữ liệu lịch sử.
    #
    # Review Finding 1 — nếu caller CÓ khai `project_id` tường minh (vd. Hub
    # UI muốn tự khẳng định Project đang active của nó khớp với run), enforce
    # đúng bằng `require_project_context_match` — phát hiện Project context
    # phía client đã trôi khỏi run thật, thay vì âm thầm cancel/stream nhầm
    # run thuộc Project khác mà request không hề hay biết. Không khai thì giữ
    # nguyên hành vi cũ (chỉ resolve+verify từ run đã lưu) — không phá caller
    # hiện có.
    if owned_run.project_id:
        await verify_project_context(plane, identity, owned_run.project_id)
        if project_id is not None:
            require_project_context_match(
                request_project_id=project_id,
                persisted_project_id=owned_run.project_id,
            )

    # Authority thật cho việc "run có thực sự bị cancel không" là repository
    # (CAS atomic transition_run_status), KHÔNG phải plane.kernel.cancel() —
    # kernel.cancel() chỉ update `_cancelled_runs` in-memory (fast-path,
    # per-instance, không thấy được các worker/process khác) rồi TỰ NÓ cũng
    # gọi cancel_run bên trong, nhưng route không được tin giá trị bool nó trả
    # về là nguồn sự thật. Gọi trực tiếp repository.cancel_run ở đây để route
    # tự xác định kết quả, độc lập với việc kernel có đang chạy run này trong
    # cùng process hay không.
    #
    # reason dùng CHUNG cho cả 2 lệnh gọi bên dưới: cancel_run cho phép CAS
    # CANCELLED->CANCELLED (idempotent, xem docstring RunRepository.cancel_run)
    # nên lệnh gọi kernel.cancel() ngay sau đây — dù chỉ là no-op về status —
    # vẫn TỰ NÓ ghi lại error_details một lần nữa qua COALESCE. Nếu 2 lệnh
    # gọi dùng reason khác nhau, lệnh thứ hai sẽ âm thầm đè lý do cancel có
    # định danh (principal_id) bằng thông điệp generic của kernel — bug đã
    # phát hiện ở review, sửa bằng cách truyền đúng 1 reason cho cả hai.
    cancel_reason = f"Cancelled via HTTP API by {identity.principal_id}"
    cancelled_record = await plane.repository.cancel_run(run_id, reason=cancel_reason)
    # Vẫn gọi kernel.cancel() để kernel có cơ hội dừng công việc in-process
    # (fast-path _cancelled_runs) nếu run đang chạy ngay trong worker này.
    await plane.kernel.cancel(run_id, reason=cancel_reason)

    if cancelled_record is None:
        # Run không tồn tại nữa giữa lúc get_scoped_run và cancel_run — coi
        # như đã biến mất.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    result_status = cancelled_record.status.value.upper()

    if cancelled_record.status.value == "cancelled":
        # Emit khi run về CANCELLED — kể cả khi nó đã CANCELLED từ trước lệnh
        # gọi này (idempotent: client gọi cancel lại vẫn hợp lệ nhận sự kiện).
        # KHÔNG emit khi run đang/đã ở một trạng thái terminal KHÁC
        # (COMPLETED/FAILED) — emit run.cancelled ở đó sẽ là nói dối vì run
        # chưa từng thực sự bị cancel.
        await stream_mgr.emit(
            plane.stream_event_repository,
            run_id=run_id,
            conversation_id=owned_run.conversation_id or "unknown",
            event_type="run.cancelled",
            payload={"run_id": run_id},
            activity_service=plane.project_activity_service,
            workspace_id=identity.workspace_id,
            project_id=owned_run.project_id,
        )

    return CancelRunResponse(run_id=run_id, status=result_status)


# 8. GET /agent/runs/{run_id}/events
@router.get("/runs/{run_id}/events")
async def get_run_events(
    request: Request,
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    project_id: str | None = Query(None),
    since_sequence: int | None = Query(None),
    last_event_id: int | None = Header(None, alias="Last-Event-ID"),
):
    plane = get_cosa_plane(request)
    owned_run = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    if owned_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Project-scoped Founder Hub — resolve Project từ run đã lưu rồi verify
    # qua Company (cùng lý do với cancel_run ở trên). Nếu caller khai
    # project_id tường minh, enforce khớp với Project thật của run (Review
    # Finding 1).
    if owned_run.project_id:
        await verify_project_context(plane, identity, owned_run.project_id)
        if project_id is not None:
            require_project_context_match(
                request_project_id=project_id,
                persisted_project_id=owned_run.project_id,
            )

    stream_mgr = get_cosa_event_stream_manager()
    effective_sequence = since_sequence if since_sequence is not None else last_event_id

    return StreamingResponse(
        stream_mgr.stream_events(
            plane.stream_event_repository, run_id, since_sequence=effective_sequence
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def create_cosa_router() -> APIRouter:
    return router
