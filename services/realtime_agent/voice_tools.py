import os
import sys

from livekit.agents import RunContext, function_tool

from event_bridge import publish_ui_command

# services/realtime_agent is a separate deploy unit from backend/app, but
# reuses its tool-bridge functions directly (SessionLocal(), no internal HTTP
# hop) rather than duplicating the DB/service-layer logic here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

try:
    from db.session import SessionLocal  # noqa: E402
    from integrations.realtime import tools as backend_tools  # noqa: E402
    from platform_core.license import tools as runtime_tools  # noqa: E402
    from founder_os.strategy import tools as strategy_tools  # noqa: E402
    from platform_core.vault import vault_tools  # noqa: E402
    from core.tool_bootstrap import load_all_tools  # noqa: E402
    from core.tool_registry import available_tools  # noqa: E402
    load_all_tools()
except Exception:
    SessionLocal = None
    backend_tools = None
    runtime_tools = None
    strategy_tools = None
    vault_tools = None

# Whitelist enforced here, not left to the model - voice commands must not be
# able to fabricate a navigation route (mCOSA V12.1 §57). The last three are
# the V13.1 Company Runtime screens; they must stay in sync with the cases in
# HologramHubController::handleVoiceNavigation, which silently falls back to
# the dashboard for anything this set rejects.
NAVIGATION_TARGETS = {
    "dashboard",
    "home",
    "cycle",
    "tasks",
    "ai_team",
    "finance",
    "vault",
    "settings",
    "strategy",
    "next_actions",
    "needs_you",
    "blocked_work",
    "work_inspector",
    "timeline_detail",
    "report_detail",
    "proposal_detail",
}


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


def _get_cycle_status_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_cycle_status(db, workspace_id)
    finally:
        db.close()


def _get_weekly_mission_impl(workspace_id: int, week_no: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_weekly_mission(db, workspace_id, week_no)
    finally:
        db.close()


def _get_function_status_impl(workspace_id: int, function: str) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_function_status(db, workspace_id, function)
    finally:
        db.close()


def _get_finance_snapshot_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return backend_tools.get_finance_snapshot(db, workspace_id)
    finally:
        db.close()


# --- V13.1 Company Runtime -------------------------------------------------
# Same SessionLocal-per-call shape as the tools above. The write-path services
# (review/rework/handoff/resolve_blocker) commit internally, so closing the
# session here does not discard them.


def _runtime_get_status_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_get_status(db, workspace_id)
    finally:
        db.close()


def _runtime_get_dag_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_get_dag(db, workspace_id)
    finally:
        db.close()


def _runtime_get_blockers_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_get_blockers(db, workspace_id)
    finally:
        db.close()


def _runtime_resolve_blocker_impl(workspace_id: int, blocker_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_resolve_blocker(db, workspace_id, blocker_id)
    finally:
        db.close()


def _runtime_get_needs_you_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_get_needs_you(db, workspace_id)
    finally:
        db.close()


def _runtime_create_handoff_impl(
    workspace_id: int, from_function: str, to_function: str, handoff_type: str, requested_action: str
) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_create_handoff(
            db, workspace_id, from_function, to_function, handoff_type, requested_action
        )
    finally:
        db.close()


def _work_review_impl(workspace_id: int, user_id: int, outcome_id: int, result: str, feedback: str | None) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.work_review(db, workspace_id, outcome_id, result, feedback, user_id)
    finally:
        db.close()


def _work_rework_impl(workspace_id: int, user_id: int, outcome_id: int, feedback: str) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.work_rework(db, workspace_id, outcome_id, feedback, user_id)
    finally:
        db.close()


def _work_get_inspector_impl(workspace_id: int, task_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.work_get_inspector(db, workspace_id, task_id)
    finally:
        db.close()


def _runtime_get_checkpoint_status_impl(workspace_id: int) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.runtime_get_checkpoint_status(db, workspace_id)
    finally:
        db.close()


# --- Dữ liệu nền: Project / OKR / Task -------------------------------------
# list_projects là bước tra TÊN -> id còn thiếu: get_project_status đòi Snowflake ID mà
# người dùng thì luôn gọi dự án bằng tên, nên trước đây model không có đường nào ngoài đoán.


def _list_projects_impl(workspace_id: int, query: str | None, limit: int) -> dict:
    db = SessionLocal()
    try:
        return strategy_tools.list_projects(db, workspace_id, query, limit)
    finally:
        db.close()


def _list_okrs_impl(workspace_id: int, cycle_id: int | None) -> dict:
    db = SessionLocal()
    try:
        return strategy_tools.list_okrs(db, workspace_id, cycle_id)
    finally:
        db.close()


def _list_tasks_impl(
    workspace_id: int, status: str | None, function: str | None, limit: int
) -> dict:
    db = SessionLocal()
    try:
        return strategy_tools.list_tasks(db, workspace_id, status, function, limit)
    finally:
        db.close()


def _get_project_roadmap_impl(workspace_id: int, project_id: str) -> dict:
    db = SessionLocal()
    try:
        return strategy_tools.get_project_roadmap(db, workspace_id, project_id)
    finally:
        db.close()


def _save_and_confirm_roadmap_impl(
    workspace_id: int,
    user_id: int,
    stages: list[dict],
    project_id: int | None = None,
    project_title: str | None = None,
    confirm_immediately: bool = True,
) -> dict:
    db = SessionLocal()
    try:
        return runtime_tools.project_save_and_confirm_roadmap(
            db, workspace_id, user_id, stages, project_id, project_title, confirm_immediately
        )
    finally:
        db.close()


def _vault_save_document_impl(
    workspace_id: int, user_id: int, path: str, content: str, kind: str = "strategy"
) -> dict:
    db = SessionLocal()
    try:
        return vault_tools.vault_save_document(db, workspace_id, user_id, path, content, kind)
    finally:
        db.close()


def _vault_list_documents_impl(
    workspace_id: int, query: str | None = None, kind: str | None = None
) -> dict:
    db = SessionLocal()
    try:
        return vault_tools.vault_list_documents(db, workspace_id, query, kind)
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
        'dashboard', 'tasks', 'vault', 'strategy', 'next_actions',
        'needs_you', 'blocked_work', 'work_inspector'. Không có route riêng
        theo từng project - `project_name` chỉ dùng để bạn nhắc lại bằng lời,
        không dùng để deep-link."""
        return _open_navigation_impl(_publish_ui_command, target, project_name)

    @function_tool
    async def get_cycle_status() -> dict:
        """Lấy trạng thái Company Cycle hiện tại."""
        return _get_cycle_status_impl(workspace_id)

    @function_tool
    async def get_weekly_mission(week_no: int) -> dict:
        """Lấy Weekly Mission theo số tuần 1-13."""
        return _get_weekly_mission_impl(workspace_id, week_no)

    @function_tool
    async def get_function_status(function: str) -> dict:
        """Lấy số lượng Task và Outcome của một AI Function."""
        return _get_function_status_impl(workspace_id, function)

    @function_tool
    async def get_finance_snapshot() -> dict:
        """Chỉ đọc snapshot cash, burn và runway; không thay đổi dữ liệu tài chính."""
        return _get_finance_snapshot_impl(workspace_id)

    @function_tool
    async def get_runtime_status() -> dict:
        """Lấy tổng quan Company Runtime: việc đang chạy, đang chờ, đang tắc."""
        return _runtime_get_status_impl(workspace_id)

    @function_tool
    async def get_dependency_graph() -> dict:
        """Lấy đồ thị phụ thuộc giữa các Task - dùng để trả lời 'vì sao
        Marketing đang phải chờ?'."""
        return _runtime_get_dag_impl(workspace_id)

    @function_tool
    async def get_blockers() -> dict:
        """Trả lời câu hỏi 'Đang tắc ở đâu?' - liệt kê các blocker đang mở."""
        return _runtime_get_blockers_impl(workspace_id)

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def resolve_blocker(blocker_id: int) -> dict:
        """Đánh dấu một blocker đã được xử lý xong theo blocker_id."""
        return _runtime_resolve_blocker_impl(workspace_id, blocker_id)

    @function_tool
    async def get_needs_you() -> dict:
        """Trả lời câu hỏi 'Việc gì cần tôi?' - hàng đợi ngoại lệ của founder."""
        return _runtime_get_needs_you_impl(workspace_id)

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def create_handoff(
        from_function: str, to_function: str, handoff_type: str, requested_action: str
    ) -> dict:
        """Tạo một handoff có cấu trúc giữa hai AI Function."""
        return _runtime_create_handoff_impl(
            workspace_id, from_function, to_function, handoff_type, requested_action
        )

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def review_work(outcome_id: int, result: str = "ACCEPTED", feedback: str | None = None) -> dict:
        """Duyệt kết quả một Outcome. `result` là 'ACCEPTED' hoặc
        'REWORK_REQUIRED'. Đây là review chất lượng đầu ra, không phải approve
        một hành động rủi ro."""
        return _work_review_impl(workspace_id, user_id, outcome_id, result, feedback)

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def request_rework(outcome_id: int, feedback: str) -> dict:
        """Yêu cầu làm lại một Outcome kèm hướng dẫn cụ thể trong `feedback`."""
        return _work_rework_impl(workspace_id, user_id, outcome_id, feedback)

    @function_tool
    async def get_work_inspector(task_id: int) -> dict:
        """Lấy toàn bộ dấu vết vận hành của một Task: contract, phụ thuộc,
        review, handoff, blocker, artifact."""
        return _work_get_inspector_impl(workspace_id, task_id)

    @function_tool
    async def get_checkpoint_status() -> dict:
        """Chỉ đọc trạng thái checkpoint gần nhất của runtime. Việc tạo
        checkpoint và resume do hệ thống tự kích hoạt, không qua giọng nói."""
        return _runtime_get_checkpoint_status_impl(workspace_id)

    @function_tool
    async def list_projects(query: str | None = None, limit: int = 20) -> dict:
        """Liệt kê các Project THẬT của công ty kèm trạng thái, giai đoạn, độ ưu
        tiên. Khi người dùng nhắc tên một dự án, LUÔN gọi tool này trước để lấy
        id, rồi mới gọi get_project_status - đừng bao giờ tự đoán project_id.
        `query` lọc theo một phần tên dự án."""
        return _list_projects_impl(workspace_id, query, limit)

    @function_tool
    async def list_okrs(cycle_id: int | None = None) -> dict:
        """Đọc OKR THẬT: chu kỳ hiện tại, các Objective và Key Result kèm giá trị
        hiện tại, mục tiêu và phần trăm tiến độ. Dùng cho mọi câu hỏi về OKR,
        mục tiêu hay chỉ số đang ở đâu. Để trống `cycle_id` để lấy chu kỳ mới nhất."""
        return _list_okrs_impl(workspace_id, cycle_id)

    @function_tool
    async def list_tasks(
        status: str | None = None, function: str | None = None, limit: int = 20
    ) -> dict:
        """Liệt kê Task THẬT của công ty, mặc định chỉ trả việc chưa xong. Dùng khi
        người dùng hỏi đang có việc gì, việc nào sắp tới hạn, việc của một
        function cụ thể."""
        return _list_tasks_impl(workspace_id, status, function, limit)

    @function_tool
    async def get_project_roadmap(project_id: str) -> dict:
        """Tra cứu chi tiết các Stage trong MVP Roadmap của Project và trạng thái thực thi hiện tại."""
        return _get_project_roadmap_impl(workspace_id, project_id)

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def save_and_confirm_roadmap(
        stages: list[dict],
        project_id: int | None = None,
        project_title: str | None = None,
        confirm_immediately: bool = True,
    ) -> dict:
        """Tạo, lưu và xác nhận MVP Roadmap vào cơ sở dữ liệu cho dự án khi founder yêu cầu lưu lộ trình.
        `stages` là danh sách các giai đoạn (mỗi giai đoạn gồm title, hypothesis, scope, exit_criteria)."""
        return _save_and_confirm_roadmap_impl(
            workspace_id, user_id, stages, project_id, project_title, confirm_immediately
        )

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def save_vault_document(path: str, content: str, kind: str = "strategy") -> dict:
        """Lưu tài liệu tri thức (Markdown) vào Knowledge Vault của workspace (kế hoạch, spec, ADR, báo cáo)."""
        return _vault_save_document_impl(workspace_id, user_id, path, content, kind)

    @function_tool
    async def list_vault_documents(query: str | None = None, kind: str | None = None) -> dict:
        """Tra cứu danh sách tài liệu tri thức Markdown hiện có trong Knowledge Vault của workspace."""
        return _vault_list_documents_impl(workspace_id, query, kind)

    wrappers = {
        "company.ceo_brief": get_ceo_brief,
        "company.next_best_actions": get_next_best_actions,
        "company.project_status": get_project_status,
        "company.portfolio_status": get_portfolio_status,
        "tech.developer_job_status": get_developer_job_status,
        "tech.request_developer_job": request_developer_job,
        "approval.pending": get_pending_approvals,
        "approval.approve": approve_action,
        "approval.reject": reject_action,
        "cycle.status": get_cycle_status,
        "cycle.weekly_mission": get_weekly_mission,
        "company.function_status": get_function_status,
        "finance.snapshot": get_finance_snapshot,
        # V13.1 Company Runtime. runtime.classify_intent is deliberately absent:
        # it is registered for internal callers only, not a founder voice command.
        "runtime.get_status": get_runtime_status,
        "runtime.get_dag": get_dependency_graph,
        "runtime.get_blockers": get_blockers,
        "runtime.resolve_blocker": resolve_blocker,
        "runtime.get_needs_you": get_needs_you,
        "runtime.create_handoff": create_handoff,
        "runtime.get_checkpoint_status": get_checkpoint_status,
        "work.review": review_work,
        "work.rework": request_rework,
        "work.get_inspector": get_work_inspector,
        # Dữ liệu nền, không gắn feature flag nào - luôn có mặt.
        "strategy.list_projects": list_projects,
        "strategy.get_project_roadmap": get_project_roadmap,
        "strategy.list_okrs": list_okrs,
        "tasks.list_tasks": list_tasks,
        "project.save_and_confirm_roadmap": save_and_confirm_roadmap,
        "vault.save_document": save_vault_document,
        "vault.list_documents": list_vault_documents,
    }
    db = SessionLocal()
    try:
        enabled_names = {spec.qualified_name for spec in available_tools(db, workspace_id)}
    finally:
        db.close()
    return [tool for name, tool in wrappers.items() if name in enabled_names] + [open_navigation]
