import os
import sys

from livekit.agents import RunContext, function_tool

from event_bridge import publish_ui_command

# services/realtime_agent is a separate deploy unit from backend/app, but
# reuses its tool-bridge functions directly (SessionLocal(), no internal HTTP
# hop) rather than duplicating the DB/service-layer logic here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.modules.realtime import tools as backend_tools  # noqa: E402

# Whitelist enforced here, not left to the model - voice commands must not be
# able to fabricate a navigation route (mCOSA V12.1 §57).
NAVIGATION_TARGETS = {"dashboard", "tasks", "vault", "strategy", "next_actions"}


def _get_ceo_brief_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_ceo_brief(db, workspace_id)
    finally:
        db.close()


def _get_next_best_actions_impl(workspace_id: int, user_id: int, limit: int = 5) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_next_best_actions(db, workspace_id, user_id, limit)
    finally:
        db.close()


def _get_project_status_impl(workspace_id: int, project_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_project_status(db, workspace_id, project_id)
    finally:
        db.close()


def _get_portfolio_status_impl(workspace_id: int, user_id: int, portfolio_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_portfolio_status(db, workspace_id, user_id, portfolio_id)
    finally:
        db.close()


def _get_developer_job_status_impl(workspace_id: int, job_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_developer_job_status(db, workspace_id, job_id)
    finally:
        db.close()


def _request_developer_job_impl(workspace_id: int, user_id: int, title: str, voice_command_id: str) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.request_developer_job(db, workspace_id, user_id, title, voice_command_id)
    finally:
        db.close()


def _get_pending_approvals_impl(workspace_id: int, limit: int = 5) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_pending_approvals(db, workspace_id, limit)
    finally:
        db.close()


def _approve_action_impl(workspace_id: int, user_id: int, step_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.approve_action(db, workspace_id, user_id, step_id)
    finally:
        db.close()


def _reject_action_impl(workspace_id: int, user_id: int, step_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.reject_action(db, workspace_id, user_id, step_id)
    finally:
        db.close()


def _open_navigation_impl(publish_fn, target: str, project_name: str | None) -> dict:
    if target not in NAVIGATION_TARGETS:
        return {"ok": False, "error": f"target không hợp lệ, chỉ chấp nhận: {sorted(NAVIGATION_TARGETS)}"}
    publish_fn(target, project_name)
    return {"ok": True}


def build_tools(*, room, workspace_id: int, user_id: int):
    def _publish_ui_command(target: str, project_name: str | None) -> None:
        publish_ui_command(room, target, project_name)

    @function_tool
    async def get_ceo_brief() -> dict:
        """Lấy tổng quan CEO Brief: sức khoẻ hệ thống, KPI, tasks, workflow, knowledge của workspace hiện tại."""
        return _get_ceo_brief_impl(workspace_id)

    @function_tool
    async def get_next_best_actions(limit: int = 5) -> dict:
        """Lấy danh sách Top Next Best Actions ưu tiên cho founder hôm nay."""
        return _get_next_best_actions_impl(workspace_id, user_id, limit)

    @function_tool
    async def get_project_status(project_id: int) -> dict:
        """Lấy trạng thái hiện tại của một Project cụ thể (status, phase, gate,
        loại project, độ ưu tiên chiến lược) theo project_id."""
        return _get_project_status_impl(workspace_id, project_id)

    @function_tool
    async def get_portfolio_status(portfolio_id: int) -> dict:
        """Lấy trạng thái hiện tại của một Portfolio cụ thể theo portfolio_id."""
        return _get_portfolio_status_impl(workspace_id, user_id, portfolio_id)

    @function_tool
    async def get_developer_job_status(job_id: int) -> dict:
        """Lấy trạng thái một Developer Job (Claude Code) cụ thể theo job_id:
        status, tóm tắt diff, kết quả test."""
        return _get_developer_job_status_impl(workspace_id, job_id)

    # on_duplicate="reject" is LiveKit's own in-flight-call dedup (a second
    # identical call arriving while the first is still running is rejected
    # outright rather than executed) - defense-in-depth on top of the DB-level
    # idempotency_key, which is what actually survives a full reconnect.
    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def request_developer_job(context: RunContext, title: str) -> dict:
        """Tạo một Developer Job (Claude Code) mới với tiêu đề `title`.
        Việc thực thi diễn ra bất đồng bộ trên Desktop Device - không chờ
        job chạy xong, chỉ xác nhận đã tạo job và trả về job_id."""
        # The provider's tool-call id doubles as the idempotency key (spec
        # §70/§90.11) - a duplicate delivery of the same tool call must not
        # dispatch a second Claude Code job. This does not protect against
        # the founder re-issuing the same request in a new conversation
        # turn/session - that is a semantic-duplicate concern the agent's
        # own conversation state should catch, not a transport retry.
        return _request_developer_job_impl(workspace_id, user_id, title, context.function_call.call_id)

    @function_tool
    async def get_pending_approvals(limit: int = 5) -> dict:
        """Lấy danh sách các approval đang chờ founder duyệt (workflow step
        đang waiting_approval)."""
        return _get_pending_approvals_impl(workspace_id, limit)

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def approve_action(step_id: int) -> dict:
        """Duyệt (approve) một workflow step đang chờ duyệt theo step_id."""
        return _approve_action_impl(workspace_id, user_id, step_id)

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def reject_action(step_id: int) -> dict:
        """Từ chối (reject) một workflow step đang chờ duyệt theo step_id."""
        return _reject_action_impl(workspace_id, user_id, step_id)

    @function_tool
    async def open_navigation(target: str, project_name: str | None = None) -> dict:
        """Điều hướng màn hình Flutter. `target` phải là một trong:
        'dashboard', 'tasks', 'vault', 'strategy', 'next_actions'. Không có
        route riêng theo từng project - `project_name` chỉ dùng để bạn nhắc
        lại bằng lời, không dùng để deep-link."""
        return _open_navigation_impl(_publish_ui_command, target, project_name)

    return [
        get_ceo_brief,
        get_next_best_actions,
        get_project_status,
        get_portfolio_status,
        get_developer_job_status,
        request_developer_job,
        get_pending_approvals,
        approve_action,
        reject_action,
        open_navigation,
    ]
