# Google ADK 2.0 Integration Guide for COSA OS

> **Lưu ý:** This file described a 2026-08-20 spike (`SalesAdkPilotGraph`) that was deleted; rewritten 2026-08-21+ to describe the shipped `AdkCofounderWorkflow`.
> Tham chiếu quyết định gốc: `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md` (Quyết định 1).

---

## 1. Tổng quan kiến trúc (Overview)

Hệ thống điều phối Co-founder trong COSA Agent Platform được xây dựng dựa trên **Google Agent Development Kit (ADK 2.0 — `google-adk==2.7.0`)**, sử dụng cấu trúc đồ thị luồng (`google.adk.workflow.Workflow`) kết hợp các `FunctionNode` tất định và cơ chế ủy quyền chuyên gia bất đồng bộ (`SpecialistDelegationNode`).

### Các nguyên tắc bất biến (Core Invariants):
1. **Không bypass Governance**: Mọi tool gọi trong node ADK bắt buộc bọc qua `CosaGovernedTool` (kết nối `GovernanceKernel` + audit log `AgentToolCall`).
2. **Không bypass Model Gateway**: Mọi LLM invocation bắt buộc thông qua `CosaModelGatewayLlm` (kết nối `ModelGateway.invoke` với circuit breaker, fallback provider, và LiteLLM invoker).
3. **Durable Delegation & Async Pause/Resume**: Các tác vụ phân tích chuyên sâu (DeepSeek/Specialist) không chạy blocking trong tiến trình workflow ADK mà tạo `DelegationJob` trên durable queue. Node ADK phát tín hiệu `RequestInput` để pause session; khi specialist hoàn tất, `MissionResumeJob` sẽ đánh thức và resume session.
4. **Tenant Isolation**: Workspace context và permissions được truyền qua `RuntimeSession` state an toàn, không nhận trực tiếp từ user input chưa kiểm định.

---

## 2. Luồng thực thi đồ thị Workflow (`AdkCofounderWorkflow`)

Workflow được định nghĩa tại `backend/app/workforce/agents/orchestration/adk/workflow.py`:

```
                 [START]
                    │
                    ▼
          [CreateMissionNode]
                    │
                    ▼
       [BuildCompanyContextNode]
                    │
                    ▼
       [RiskClassificationNode] ──(needs_confirmation)──► [DRAFT / Pause for Founder]
                    │
              (auto_start)
                    ▼
             [PlanningNode]
                    │
     ┌──────────────┴──────────────┐
     ▼                             ▼
[SpecialistDelegation: TECH]  [SpecialistDelegation: MARKETING] ... (5 domains)
     └──────────────┬──────────────┘
                    ▼
          [JoinSpecialistsNode]
                    │
                    ▼
       [GovernanceGatePreSynthesis] ──(blocked)──► [ExecutionNode]
                    │
                (continue)
                    ▼
             [SynthesisNode]
                    │
                    ▼
            [QualityGateNode]
                    │
                    ▼
           [ApprovalGateNode]
                    │
                    ▼
            [ExecutionNode]
                    │
                    ▼
                  [END]
```

### Danh sách các Node chính:
1. **`CreateMissionNode`**: Khởi tạo bản ghi `MissionRun` trong database, cấp phát mission trace ID.
2. **`BuildCompanyContextNode`**: Tải hồ sơ doanh nghiệp (giai đoạn startup S0–S5, budget, KPI, knowledge embeddings).
3. **`RiskClassificationNode`**: Đánh giá cấp độ rủi ro (R0–R4). Nếu cần duyệt trước khi chạy, chuyển sang `needs_confirmation` để Founder xác nhận; nếu không, tiếp tục `auto_start`.
4. **`PlanningNode`**: Lập kế hoạch hành động đa chuyên gia (Specialist Action Plan) sử dụng mô hình qua `CosaModelGatewayLlm`.
5. **`SpecialistDelegationNode` & `JoinSpecialistsNode`**: Ủy quyền song song cho 5 domain (TECH, MARKETING, SALES, LEGAL, FINANCE) qua `TaskBoardService`/`DelegationJob`. Node tạm dừng và khôi phục trạng thái bằng cơ chế Event-driven Resume.
6. **`GovernanceGatePreSynthesis`**: Kiểm tra rủi ro, quota chi phí và stuck-prevention trước khi tổng hợp kết quả.
7. **`SynthesisNode`**: Tổng hợp các work products từ specialist thành chiến lược/báo cáo đồng nhất.
8. **`QualityGateNode`**: Kiểm định chất lượng đầu ra (completeness, accuracy, actionable steps).
9. **`ApprovalGateNode`**: Tạo `AgentApproval` nếu có hành động rủi ro cần Founder phê duyệt trước khi thi hành.
10. **`ExecutionNode`**: Chuyển trạng thái mission sang `COMPLETED` (hoặc `FAILED`/`BLOCKED`), xuất work product cuối cùng.

---

## 3. Các Seam & Thành phần Tích hợp

### 3.1. Seam điều phối: `AdkCofounderOrchestratorService`
Nằm tại `backend/app/workforce/agents/orchestration/service.py`. Là điểm tiếp nhận duy nhất cho toàn bộ request mission từ API router (`/api/v1/agents/mission-control`), cung cấp các phương thức:
- `start_mission(...)`: Khởi tạo session ADK và chạy workflow.
- `confirm_mission(...)`: Tiếp tục workflow sau khi Founder phê duyệt bản draft.
- `resume_mission(...)`: Đánh thức workflow khi các `DelegationJob` của specialist hoàn tất.

### 3.2. Governance Tool: `CosaGovernedTool`
Nằm tại `backend/app/workforce/agents/orchestration/adk/governed_tool.py`.
Bọc các công cụ nội bộ thành chuẩn `google.adk.tools.BaseTool`:
- Thực thi chính sách phân quyền (L0 Read-only, L1 Internal Mutating, L2 External, L3 Financial).
- Ghi log `AgentToolCall` bắt buộc trước và sau khi tool chạy.
- Kết nối `GovernanceKernel` để kiểm tra quota, rate limit và approval ticket.

### 3.3. Model Gateway Adapter: `CosaModelGatewayLlm`
Nằm tại `backend/app/workforce/agents/orchestration/adk/model_adapter.py`.
Bọc ADK Model interface sang `ModelGateway.invoke()`:
- Đảm bảo typed system instruction và message history được truyền đúng tới provider qua `cosa_litellm_invoker`.
- Tự động kích hoạt Circuit Breaker nếu provider (OpenAI, Anthropic, DeepSeek, Kira AI) gặp sự cố liên tiếp.

### 3.4. Session State & Resume: `RuntimeSession` & `MissionResumeJob`
Nằm tại `backend/app/workforce/agents/orchestration/adk/session_bridge.py` và `mission_resume_service.py`.
- Sử dụng bảng `runtime_sessions` và `runtime_session_events` để lưu trữ tuần tự hóa trạng thái workflow.
- `MissionResumeJob` đảm bảo tính chất **exactly-once execution**: khi nhiều specialist kết thúc đồng thời, chỉ có đúng 1 lệnh resume được trigger cho mission tương ứng.
