# COSA Hologram Hub & Runtime Integration Plan
**Bản Kế Hoạch Hiện Thực Hoá AI Business Operating System (OPC Command Center)**
*Dựa trên tài liệu phân tích chuyên sâu [abc.md](../abc.md)*

---

## 1. Bối Cảnh & Đánh Giá Kiến Trúc

### 1.1 Điểm Mạnh Đã Đạt Được
- **Founder Command Center (Bố cục 3 Cột)**: 
  - Cột Trái: Báo cáo điều hành & hàng đợi việc cần Founder can thiệp.
  - Cột Giữa: Hologram Visualizer & Workspace ngữ cảnh.
  - Cột Phải: Chat / Voice Command Interface.
  - Phía Dưới: Thanh Business Pulse tổng hợp theo thời gian thực.
- **Mô hình One Person Company (OPC)**: Đã định hình rõ ràng chu trình "Subagents thực thi $\rightarrow$ COSA tổng hợp $\rightarrow$ Founder ra quyết định".
- **Không Đập Đi Xây Lại**: Giữ nguyên 70–80% bộ khung UI/UX hiện tại, tập trung toàn lực vào việc nối **Live Runtime** vào các thành phần trên màn hình.

### 1.2 Những Điểm Cần Khắc Phục Cốt Lõi
1. **Hologram Orb Data-Driven**: Quả cầu 3D không còn là hoạt ảnh ngẫu nhiên mà đại diện cho đồ thị hệ thống thực tế (Nodes: COSA Core, Revenue Agent, Research Agent, Finance Agent, Execution Agent, Projects, OKRs) với màu sắc ngữ nghĩa (🟢 Healthy, 🟡 Pending Approval, 🔴 Blocker, 🔵/Pulse Active).
2. **Quick Actions chuyển thành Typed Capability Pipeline**:
   - Thay vì gửi câu chat text thô (`executePrompt(...)`), Quick Action gọi trực tiếp pipeline:
     $$\text{Intent} \rightarrow \text{Capability} \rightarrow \text{Versioned Prompt (@v1.x)} \rightarrow \text{Tool Layer} \rightarrow \text{Telemetry Logging}$$
3. **Cột Trái ưu tiên "NEEDS YOU" số 1**:
   - Đưa hàng đợi ngoại lệ / phê duyệt của Founder lên đầu bảng với số lượng và lý do cụ thể (*"Why COSA flagged this"*).
4. **Bottom Bar thành "Business Pulse"**:
   - Hiển thị tình trạng hoạt động 2 dòng (Active/Healthy, Open/At risk, On track).
5. **Bộ 3 Chế Độ Vận Hành (Operating Modes)**:
   - 👑 **Founder Mode**: Điều hành doanh nghiệp, xem KPI, phê duyệt ngoại lệ.
   - ⚙️ **Operator Mode**: Giám sát hàng đợi công việc của Agent, trạng thái worker.
   - 🔬 **Developer Mode**: Quan sát Telemetry kỹ thuật (Run ID, Capability, Prompt Version, Model, Tools Used, Latency).

---

## 2. Kiến Trúc Hệ Thống (Target Architecture)

```text
                    ┌─────────────────────────────────────────────────┐
                    │               HOLOGRAM HUB (UI)                 │
                    │  [Needs You]  [Data-Driven Core]  [Chat/Voice]  │
                    │  [Timeline]   [Live Telemetry]    [Quick Acts]  │
                    │  [Pulse Bar]  [Drilldown Drawer]  [3-Mode Tgl]  │
                    └────────────────────────┬────────────────────────┘
                                             │
                                             ▼
                     REST API (/api/v1/admin) & SSE Stream
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────┐
                    │              INTENT & GATE ROUTER               │
                    │  (Social Chat vs. Typed Intent vs. Deep Task)   │
                    └────────────────────────┬────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────┐
                    │               COSA ORCHESTRATOR                 │
                    │  ├─ ContextResolver (Cycle, OKRs, Work, Cash)   │
                    │  ├─ Capability Registry (DailyBrief, OKRReview) │
                    │  ├─ Prompt Registry (Versioned Prompts @v1.x)   │
                    │  └─ Tool Layer (DB Repositories, Sandboxes)     │
                    └────────────────────────┬────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────┐
                    │         AGENT RUNS & AUDIT TELEMETRY            │
                    │  (Run ID, Tools Used, Latency, Token Metrics)   │
                    └──────────────┬───────────────────┬──────────────┘
                                   │                   │
                                   ▼                   ▼
                          Hologram State          Founder Cards
                         (Live Node Graph)       (Actionable Queues)
```

---

## 3. Tiêu Chuẩn 5 Câu Hỏi Audit Cho Mọi Capability

Để đảm bảo AI không chỉ là generic chatbot, mọi Quick Action và Capability trong COSA phải trả lời được 5 câu hỏi:

| Câu hỏi Audit | Định nghĩa | Ví dụ: Quick Action "Tổng quan hôm nay" |
|---|---|---|
| **1. Prompt nằm ở đâu?** | File/Module lưu trữ prompt template | `app/agents/capabilities/quick_action_service.py` |
| **2. Prompt version nào đang dùng?** | Phiên bản được gắn thẻ rõ ràng | `daily_brief@v1.2.0` |
| **3. Agent / Capability nào gọi?** | Tên định danh capability trong catalog | `operations.daily_brief` |
| **4. Tools nào agent được phép gọi?** | Danh sách Repository / Tool được cấp quyền | `["CycleRepository", "OKRRepository", "WorkRepository", "ProjectRepository"]` |
| **5. Agent run có log lại không?** | Run ID, Latency, Telemetry có được ghi nhận | `Run ID: Snowflake ID`, `Latency: 28ms`, `Telemetry: Captured` |

---

## 4. Kế Hoạch & Chi Tiết Triển Khai (Roadmap)

### 4.1 Backend
- [x] **Tạo dịch vụ Quick Action**: [`backend/app/agents/capabilities/quick_action_service.py`](../backend/app/agents/capabilities/quick_action_service.py)
  - `daily_brief` $\rightarrow$ `operations.daily_brief` (`daily_brief@v1.2.0`)
  - `okr_check` $\rightarrow$ `strategy.okr_review` (`okr_progress_review@v1.1.0`)
  - `task_prioritize` $\rightarrow$ `execution.prioritizer` (`execution_prioritize@v1.0.0`)
  - `finance_summary` $\rightarrow$ `finance.summary` (`finance_snapshot@v1.0.0`)
- [x] **Mở rộng Hub Summary API**: [`backend/app/modules/platform/hub_service.py`](../backend/app/modules/platform/hub_service.py)
  - Trả về cấu trúc `needs_you`, `business_pulse` và `runtime_graph` (đồ thị nodes Agent thực tế).
- [x] **Thêm Endpoint thực thi Capability**: [`backend/app/modules/platform/router.py`](../backend/app/modules/platform/router.py)
  - `POST /api/v1/admin/{workspace_id}/quick-actions/execute`
- [x] **Viết Unit Tests Backend**: [`backend/app/tests/test_quick_action_service.py`](../backend/app/tests/test_quick_action_service.py)

### 4.2 Frontend (Flutter)
- [x] **Cập nhật Hub Service**: [`frontend/lib/data/services/hub_service.dart`](../frontend/lib/data/services/hub_service.dart)
  - Thêm phương thức `executeQuickAction(actionKey)`.
- [x] **Nâng cấp Controller**: [`frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart`](../frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart)
  - Thêm quản lý 3 Chế Độ Vận Hành (`operatingMode`: `founder`, `operator`, `developer`).
  - Thêm `runQuickAction` kết nối trực tiếp backend và lưu `latestTelemetry`.
- [x] **Tái cấu trúc Cột Trái (Executive Report)**: [`frontend/lib/modules/hologram_hub/presentation/widgets/executive_report_panel.dart`](../frontend/lib/modules/hologram_hub/presentation/widgets/executive_report_panel.dart)
  - Đưa block **`NEEDS YOU`** lên đầu tiên kèm badge cảnh báo.
  - Tích hợp Modal **"Reason for Attention"** (*Why COSA flagged this*, Khuyến nghị, Nút hành động).
- [x] **Nâng cấp Quick Commands Bar**: [`frontend/lib/modules/hologram_hub/presentation/widgets/quick_commands_bar.dart`](../frontend/lib/modules/hologram_hub/presentation/widgets/quick_commands_bar.dart)
  - Đồng bộ các nút lệnh nhanh với danh mục OPC Action.
- [x] **Thêm Bộ Chuyển Đổi Operating Mode ở Header**: [`frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`](../frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart)
  - Menu chuyển đổi giữa 👑 Founder Mode, ⚙️ Operator Mode và 🔬 Developer Mode.

---

## 5. Kết Quả Xác Minh (Verification)

### 5.1 Backend Tests
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/app/tests/test_quick_action_service.py backend/app/tests/test_platform_hub_summary.py backend/app/tests/test_platform_audit_events.py -v
# Output: 8 passed in 0.03s
```

### 5.2 Frontend Tests & Static Analysis
```bash
flutter analyze lib/modules/hologram_hub/
# Output: No issues found!

flutter test test/quick_commands_bar_test.dart test/hologram_hub_test.dart test/hub_service_test.dart test/kpi_strip_test.dart test/miva_hologram_core_test.dart
# Output: 16 passed! All tests passed!
```
