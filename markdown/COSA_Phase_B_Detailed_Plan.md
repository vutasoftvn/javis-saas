# Kế Hoạch Triển Khai Chi Tiết: Phase B (Backend & Frontend)
## Quản Trị Hệ Thống (Governance), Cổng Phê Duyệt Nhân Sự (Human Authority Gate), Ngân Sách (Budget Engine) & Sổ Cái Chi Phí (Cost Ledger)

- **Trạng thái:** Bản kế hoạch chính thức (Ready for Implementation)
- **Tài liệu tham chiếu:** `markdown/D3-COSA_Paperclip_Agent_Workforce_Integration.md` (Mục 11, 13, 14, 15, 16, 24, 49)
- **Phạm vi:** Backend (FastAPI + SQLAlchemy) & Frontend (Flutter + GetX)

---

## 1. NGUYÊN TẮC KIẾN TRÚC & QUY TẮC BẮT BUỘC TRONG PHASE B

```mermaid
graph TD
    AgentAction[Agent Proposes Action / Tool Exec] --> PermCheck{1. Permission Engine}
    PermCheck -->|Denied| BlockPerm[Permission Denied 403]
    PermCheck -->|Allowed| RiskEval{2. Risk Policy Evaluation}
    
    RiskEval -->|LOW (Read, Draft, Research)| AutoExec[Auto-Execute]
    RiskEval -->|MEDIUM (Internal Task, Non-critical CRM)| ExecNotify[Execute + Audit/Notify]
    RiskEval -->|HIGH (Email, Zalo, Deploy, Accounting)| CreateTicket[Create Approval Request]
    RiskEval -->|CRITICAL (API Keys, System Prompts, Specs)| BlockCritical[Founder Only / Hard Block]
    
    CreateTicket --> Inbox[Human Approval Inbox - Flutter UI]
    Inbox -->|Founder Approves| ResumeExec[Resume Execution Pipeline]
    Inbox -->|Founder Rejects| TerminateExec[Terminate with Reason]
    Inbox -->|Request Revision| FeedbackLoop[Agent Self-Correction / Revise]

    AutoExec --> BudgetCheck{3. Budget Engine Check}
    ExecNotify --> BudgetCheck
    ResumeExec --> BudgetCheck
    
    BudgetCheck -->|< 80%| NormalRun[Execute Normally]
    BudgetCheck -->|80% - 89%| WarnRun[Execute + Warning Alert]
    BudgetCheck -->|90% - 99%| UrgentRun[Execute + Urgent Warning Alert]
    BudgetCheck -->|100% (Hard Stop)| CircuitBreaker[Block Execution / Quota Exceeded]
    
    NormalRun --> CostLedger[4. Immutable Cost Ledger Ghi nhận Token, USD, VND]
    WarnRun --> CostLedger
    UrgentRun --> CostLedger
```

### 1.1. Bốn Cấp Độ Rủi Ro (4 Risk Levels):
1. **`LOW` (R0-R1)**: Tự động chạy không cần duyệt (Research, đọc CRM, tóm tắt dữ liệu, draft bản thảo).
2. **`MEDIUM` (R2)**: Tự động chạy nhưng ghi nhật ký & gửi thông báo cho Lead/Founder (tạo internal task, cập nhật CRM phi tài chính, sinh đề xuất chiến dịch).
3. **`HIGH` (R3)**: Bắt buộc Founder hoặc Team Lead phê duyệt trên Inbox trước khi gọi tool (Gửi Email cho khách, gửi tin Zalo/Telegram, xuất bản mạng xã hội, Deploy Production, lập hoá đơn, sửa đổi số liệu kế toán, chi ngân sách quảng cáo).
4. **`CRITICAL` (R4)**: Chỉ Founder đích danh mới có quyền thao tác (Đọc/Ghi API Keys, chuyển khoản ngân hàng, xóa dữ liệu kế toán, sửa đổi System Prompt, sửa Build Spec, sửa Security Policy, thay đổi License). **Agent tuyệt đối bị cấm tự chỉnh sửa các tài nguyên này.**

### 1.2. Cơ Chế Ngân Sách (Budget Circuit Breaker):
- Quản trị hạn mức ngân sách AI theo 4 chiều: `Company`, `Department`, `Agent`, `Project`.
- 3 ngưỡng phản hồi tự động:
  - $\mathbf{80\%}$: Gửi cảnh báo Warning (vàng) lên Dashboard.
  - $\mathbf{90\%}$: Gửi cảnh báo Urgent Warning (cam) đến Founder.
  - $\mathbf{100\%}$: Ngắt mạch thực thi (**Hard Stop**), Agent bị khoá trạng thái `BUDGET_BLOCKED` trừ khi có Founder Override.

### 1.3. Sổ Cái Chi Phí Bất Biến (Immutable Cost Ledger):
- Mỗi lần thực thi của Agent (`AgentRun`) ghi nhận 1 bản ghi bất biến vào `cost_ledger_entries`: `trace_id`, `agent_key`, `provider`, `model_name`, `input_tokens`, `output_tokens`, `cost_usd`, `cost_vnd` (quy đổi theo tỷ giá chuẩn 25,400 VND/\$), `billing_cycle` (gắn liền với chu kỳ 12-Week Year).

---

## 2. THIẾT KẾ BACKEND (FASTAPI + SQLALCHEMY)

### 2.1. Data Models (`backend/app/agent_platform/models.py`)
1. **`UnifiedPermission`**:
   - `workspace_id`, `principal_type` (`USER` | `AGENT`), `principal_id`, `resource_type` (`TOOL` | `DATA` | `MODULE` | `BUDGET`), `resource_key` (vd: `crm.update`, `email.send`, `*`), `action` (`READ`, `WRITE`, `EXECUTE`, `ADMIN`), `is_allowed`, `requires_approval`.
2. **`ApprovalRequest`**:
   - `workspace_id`, `task_id`, `run_id`, `requester_agent_key`, `action_type`, `risk_level` (`HIGH`, `CRITICAL`), `required_role` (`LEAD`, `FOUNDER`), `status` (`PENDING`, `APPROVED`, `REJECTED`, `REVISION_REQUESTED`), `tool_key`, `payload_jsonb`, `reason`, `approver_user_id`, `approver_comment`, `approved_at`.
3. **`AgentBudget`**:
   - `workspace_id`, `agent_key`, `department`, `cycle_type` (`12_WEEK_YEAR`, `MONTHLY`), `limit_usd`, `spent_usd`, `soft_limit_percent` (mặc định 0.8), `is_blocked`, `period_start`, `period_end`.
4. **`CostLedger`**:
   - `workspace_id`, `run_id`, `task_id`, `agent_key`, `provider`, `model_name`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost_usd`, `cost_vnd`, `billing_cycle`, `meta_jsonb`.

### 2.2. Service Layer (`backend/app/agent_platform/governance/`)
- **`risk_evaluator.py`**: Chuẩn hóa phân loại 4 mức rủi ro (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) theo danh mục tool và payload.
- **`approval_service.py`**:
  - `create_request(...) -> ApprovalRequest`
  - `list_pending_requests(workspace_id, required_role) -> List[ApprovalRequest]`
  - `approve(request_id, user_id, comment) -> ApprovalRequest` (tự động kích hoạt resume task/run bị tạm dừng).
  - `reject(request_id, user_id, reason) -> ApprovalRequest`
  - `request_revision(request_id, user_id, feedback) -> ApprovalRequest`
- **`budget_service.py`**:
  - `check_budget_quota(agent_key, workspace_id) -> Dict` (ném ngoại lệ `BudgetExceededError` khi đạt 100%).
  - `record_spend(agent_key, amount_usd, workspace_id) -> AgentBudget` (cập nhật ngân sách và tự động set `is_blocked = True` khi chạm trần).
  - `set_budget_limit(agent_key, limit_usd, cycle_type) -> AgentBudget`
- **`cost_ledger_service.py`**:
  - `record_cost_entry(...) -> CostLedger`
  - `get_cost_summary(workspace_id, billing_cycle) -> Dict` (tổng hợp theo ngày, theo Agent, theo Department).
  - `list_recent_entries(...) -> List[CostLedger]`
- **`permission_engine.py`**:
  - `can(principal_type, principal_id, resource_type, resource_key, action) -> bool`
  - `grant_permission(...) -> UnifiedPermission`
  - Chặn đứng mọi nỗ lực của Agent cố gắng ghi đè System Prompts, Specs, Policies.

### 2.3. REST APIs (`backend/app/agent_platform/api/admin_api.py`)
- `GET /api/v1/agent-platform/approvals`: Lấy danh sách phiếu chờ duyệt.
- `POST /api/v1/agent-platform/approvals/{id}/approve`: Phê duyệt phiếu.
- `POST /api/v1/agent-platform/approvals/{id}/reject`: Từ chối phiếu.
- `POST /api/v1/agent-platform/approvals/{id}/request-revision`: Yêu cầu Agent sửa lại kèm feedback.
- `GET /api/v1/agent-platform/budgets`: Danh sách ngân sách theo Agent/Phòng ban.
- `POST /api/v1/agent-platform/budgets`: Thiết lập hạn mức ngân sách mới.
- `GET /api/v1/agent-platform/cost-ledger`: Tổng hợp chi phí và danh sách các lần chi tiêu token/USD/VND.
- `POST /api/v1/agent-platform/unified-permissions/grant`: Cấp quyền ma trận RBAC.

---

## 3. THIẾT KẾ FRONTEND (FLUTTER + GETX)

### 3.1. Phân Hệ 1: Human Approval Inbox (`lib/modules/approvals/`)
- **Màn hình chính `approvals_view.dart`**:
  - Danh sách thẻ phiếu duyệt phân loại theo mức rủi ro (`🔴 CRITICAL`, `🟠 HIGH`).
  - Mỗi thẻ hiển thị:
    - Agent yêu cầu (Avatar, tên Agent, vai trò).
    - Hành động cần thực thi (vd: Gửi email cho khách hàng `nguyen@example.com`, Xuất bản bài viết Facebook).
    - Lý do cần duyệt (Reason context).
    - Payload chi tiết (Nội dung email/bài viết/lệnh).
  - Thanh công cụ thao tác 1-Click:
    - 🟢 **Chấp thuận (Approve)**: Mở dialog xác nhận nhanh kèm ô ghi chú (optional).
    - 🔴 **Từ chối (Reject)**: Mở modal nhập lý do từ chối.
    - 🟡 **Yêu cầu làm lại (Request Revision)**: Nhập hướng dẫn sửa đổi để Agent viết lại.
- **Controller `approvals_controller.dart`**:
  - Reactive list `pendingApprovals = <Map<String, dynamic>>[].obs`.
  - Methods: `loadPendingApprovals()`, `approveTicket(id, comment)`, `rejectTicket(id, reason)`, `requestRevision(id, feedback)`.

### 3.2. Phân Hệ 2: Quản Trị Ngân Sách & Sổ Cái Chi Phí (`lib/modules/usage/`)
- **Màn hình `usage_view.dart` chia làm 3 khu vực**:
  1. **Thanh Đồng Hồ Đo Ngân Sách (Budget Gauges)**:
     - Biểu đồ hình tròn / Gauge Bar hiển thị `% Spent` tổng công ty và từng Agent.
     - Đổi màu động: Xanh lục ($<80\%$), Vàng cam ($80-99\%$), Đỏ rực ($100\%$ Hard-stop).
     - Nút "Điều chỉnh hạn mức (Set Limit)" cho Founder.
  2. **Bảng Kê Chi Phí Bất Biến (Cost Ledger Data Table)**:
     - Bảng tra cứu: Trace ID, Agent, Model, Tokens (Input/Output), Chi phí (\$USD), Quy đổi (VND), Chu kỳ (12WY Q3).
     - Bộ lọc theo Agent, Phòng ban, Khoảng thời gian.
     - Nút xuất dữ liệu (Export CSV/JSON).
  3. **Biểu Đồ Phân Bổ Chi Phí (Cost Distribution Charts)**:
     - Biểu đồ cột chi phí theo ngày.
     - Biểu đồ tròn tỷ trọng chi phí AI giữa các phòng ban (Sales, Marketing, Finance, Engineering).

### 3.3. Phân Hệ 3: Ma Trận Phân Quyền Hợp Nhất (`lib/modules/settings/permissions_view.dart`)
- Bảng ma trận phân quyền giữa Principal (`User`, `Agent`) và Resources.
- Toggle switches bật/tắt quyền `READ`, `WRITE`, `EXECUTE`, `REQUIRE_APPROVAL`.

---

## 4. KẾ HOẠCH TEST SUITE CHO PHASE B (VERIFICATION PLAN)

### 4.1. Backend Test Cases (`backend/app/tests/agent_platform/test_cosa_phase_b_governance.py`):
1. `test_permission_engine_least_privilege`: Kiểm tra Agent chỉ đọc được dữ liệu được phân quyền; cấm ghi đè System Prompt / Policies.
2. `test_risk_evaluator_tiers`: Kiểm tra phân loại chính xác 4 mức `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
3. `test_approval_workflow_lifecycle`: Tạo Approval Request $\rightarrow$ Pending $\rightarrow$ Founder Approve $\rightarrow$ Task tiếp tục chạy thành công.
4. `test_budget_circuit_breaker_hard_stop`: Ghi nhận chi phí vượt 100% limit $\rightarrow$ `BudgetExceededError` được kích hoạt và chặn AgentRun tiếp theo.
5. `test_cost_ledger_immutability_and_vnd_conversion`: Ghi nhận token, USD và kiểm tra quy đổi VND chính xác (tỷ giá 25,400).

### 4.2. Frontend Test Cases:
1. Mở màn hình `Approvals`: Hiển thị chính xác các phiếu chờ duyệt với đầy đủ Payload và Risk Badge.
2. Thao tác bấm `Approve`: Phiếu biến mất khỏi danh sách chờ, thông báo thành công và task tương ứng được hoàn thành.
3. Mở màn hình `Usage`: Đồng hồ đo ngân sách hiển thị đúng % chi tiêu và bảng Cost Ledger hiển thị đầy đủ các cột Token/USD/VND.
