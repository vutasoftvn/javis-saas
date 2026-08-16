# Kế Hoạch Triển Khai Chi Tiết: Giai Đoạn P1 (Phase 1)
## Hologram Hub & CEO Command Center (Trọng Tâm Điều Hành Cho Founder)

> **Mục tiêu của Phase P1:**
> Chuyển đổi Hologram Hub từ một trang launcher thông thường thành **CEO Command Center (Trung tâm Chỉ huy Điều hành)** thực thụ cho Founder:
> - Trả lời 5 câu hỏi mỗi sáng của Founder: *Hôm nay việc gì quan trọng? Việc gì đang chờ tôi duyệt? Các Agent đang làm gì? Sức khỏe công ty ra sao? Bước tiếp theo là gì?*
> - Tích hợp thống nhất dữ liệu: **Company Pulse**, **Top 3 Việc Ưu Tiên**, **Active Missions Tracker**, **Quick Approval Cards**, và **Lối vào nhanh COSA Companion**.
> - Backend Aggregator hiệu năng cao (1 single query < 50ms) + Realtime WebSocket Event Stream.

---

## 1. Cấu Trúc Kiến Trúc & Luồng Dữ Liệu Phase P1

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FLUTTER CEO COMMAND CENTER                            │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ 1. HEADER: Good Morning Founder · Live Company Pulse (Sales, Cash, Ops)   │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │ 2. TODAY PRIORITIES: 1–3 việc trọng tâm trong ngày gắn với Kế hoạch tuần   │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │ 3. WAITING FOR YOU: Approval Cards (Duyệt email, duyệt chiến dịch, chi)   │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │ 4. ACTIVE MISSIONS: Tiến độ nhiệm vụ đa agent (Find 20 leads [72%]...)    │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │ 5. COSA QUICK INPUT: "Chúng ta nên làm gì tiếp theo?" → Mở Chat/Voice     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────▲─────────────────────────────────────────┘
                                        │ REST API (GET /hub/command-center) + WS
┌───────────────────────────────────────┴─────────────────────────────────────────┐
│                 BACKEND: FounderCommandCenterService (FastAPI)                  │
│  - Aggregator: Tính toán Pulse, lọc Top 3 Tasks, tổng hợp Approvals & Missions │
│  - Quick Action Handler: POST /hub/quick-approve (Idempotent + Audit Log)       │
│  - Realtime Hub Streamer: Broadcast sự kiện Approval mới / Mission update      │
└───────────────────────────────────────▲─────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
  Bảng tasks & plans             Bảng approvals & outbox        Bảng workflows/missions
```

---

## 2. Chi Tiết Các Nhiệm Vụ Kỹ Thuật Trong Phase P1

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TASK P1.1: Backend Founder Command Center Aggregator Service                     │
│ - Endpoint: GET /api/v1/workspaces/{workspace_id}/hub/command-center            │
│ - Tổng hợp: Company Pulse, Top 3 Tasks, Active Missions, Needs-You Approvals    │
│ - Tối ưu hóa truy vấn PostgreSQL (1 round-trip, < 50ms)                        │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P1.2: Backend Quick Approval & Action Dispatcher                            │
│ - Endpoint: POST /api/v1/workspaces/{workspace_id}/hub/quick-approve            │
│ - Snapshot verification: Đảm bảo payload duyệt không bị thay đổi ngầm           │
│ - Đẩy trực tiếp vào Outbox Queue sau khi Founder duyệt                          │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P1.3: Realtime Event Stream cho Hub (WebSocket / SSE)                      │
│ - Phát event khi: có Approval mới, Mission thay đổi tiến độ, Task hoàn thành   │
│ - Flutter tự động cập nhật UI không cần reload toàn trang                       │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P1.4: Flutter CEO Command Center UI Redesign                               │
│ - Widget: CompanyPulseBar (Chỉ số Sales, Cash, Ops có màu sắc trạng thái)       │
│ - Widget: TodayPriorityList (1–3 việc lớn có checkbox tương tác tức thì)        │
│ - Widget: QuickApprovalCard (Xem snapshot payload, nút Duyệt / Từ chối / Hỏi AI)│
│ - Widget: ActiveMissionCard (Thanh tiến độ % và hiển thị Agent phụ trách)       │
│ - Widget: CosaQuickBar (Ô lệnh nhanh chuyển mượt mà vào Chat Companion)         │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P1.5: Unit & Integration Tests cho Phase P1                                │
│ - Pytest: Test Aggregator trả đúng cấu trúc, test Quick Approve tạo outbox      │
│ - Flutter Analyze: Đảm bảo 0 lỗi linter/type error                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Đặc Tả Dữ Liệu API Contract (Backend $\leftrightarrow$ Frontend)

### 3.1 `GET /api/v1/workspaces/{workspace_id}/hub/command-center`
**Response JSON mẫu:**
```json
{
  "status": "success",
  "data": {
    "greeting": {
      "title": "Chào buổi sáng, Founder",
      "summary": "Hôm nay có 3 việc ưu tiên, 2 phê duyệt đang chờ và 3 nhiệm vụ đang chạy."
    },
    "company_pulse": {
      "sales": {"trend": "up", "status": "Tăng trưởng tốt", "indicator": "+15% tuần này", "color": "green"},
      "cash": {"trend": "neutral", "status": "Ổn định", "indicator": "Runway: 8.5 tháng", "color": "cyan"},
      "marketing": {"trend": "up", "status": "Chiến dịch Q3 đang chạy", "indicator": "120 leads", "color": "green"},
      "operations": {"trend": "check", "status": "Hoạt động bình thường", "indicator": "0 lỗi hệ thống", "color": "green"},
      "legal": {"trend": "check", "status": "Tuân thủ đầy đủ", "indicator": "Hạn thuế: 20 ngày", "color": "green"}
    },
    "today_priorities": [
      {
        "id": "123456789012345678",
        "title": "Chốt danh sách 20 khách hàng mục tiêu cho chiến dịch mới",
        "priority": "urgent",
        "due_time": "17:00",
        "status": "todo",
        "agent_assigned": "Sales Agent"
      },
      {
        "id": "123456789012345679",
        "title": "Duyệt nội dung email chào hàng trước khi gửi hàng loạt",
        "priority": "high",
        "due_time": "14:00",
        "status": "waiting_approval",
        "agent_assigned": "Marketing Agent"
      }
    ],
    "waiting_for_you": [
      {
        "approval_id": "987654321098765432",
        "title": "Duyệt gửi email tiếp cận 20 đối tác",
        "type": "outreach_email",
        "urgency": "high",
        "agent": "Sales Agent",
        "payload_preview": {
          "recipient_count": 20,
          "subject": "Giải pháp tối ưu quy trình cho doanh nghiệp",
          "channel": "Resend Email"
        },
        "created_at": "2026-08-16T08:30:00Z"
      }
    ],
    "active_missions": [
      {
        "mission_id": "555555555555555555",
        "title": "Tìm kiếm 20 khách hàng tiềm năng B2B",
        "agent": "Sales Agent",
        "status": "running",
        "progress_percent": 72,
        "current_step": "Enriching contact emails",
        "next_step": "Lead scoring & qualification"
      },
      {
        "mission_id": "555555555555555556",
        "title": "Xây dựng trang đích Landing Page ra mắt sản phẩm",
        "agent": "Marketing Agent",
        "status": "running",
        "progress_percent": 45,
        "current_step": "Generating Hero & Feature modules",
        "next_step": "Pricing table & lead capture form"
      }
    ]
  }
}
```

### 3.2 `POST /api/v1/workspaces/{workspace_id}/hub/quick-approve`
**Request Body:**
```json
{
  "approval_id": "987654321098765432",
  "decision": "approve",
  "reason": "Nội dung đạt yêu cầu, cho phép gửi."
}
```
**Response Body:**
```json
{
  "status": "success",
  "message": "Phê duyệt thành công. Tác vụ đã được chuyển vào hàng đợi Outbox.",
  "outbox_id": "112233445566778899"
}
```

---

## 4. Danh Sách Files Cần Tạo Mới & Chỉnh Sửa Trong Phase P1

### Backend (FastAPI / Python)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[NEW]** | `backend/app/modules/platform/founder_hub_service.py` | Aggregator service tính toán Pulse, Top 3, Approvals, Missions |
| **[NEW]** | `backend/app/modules/platform/founder_hub_router.py` | Router REST API: `GET /hub/command-center` & `POST /hub/quick-approve` |
| **[MODIFY]** | `backend/app/main.py` | Đăng ký `founder_hub_router` vào FastAPI app |
| **[NEW]** | `backend/app/tests/test_p1_founder_hub.py` | Pytest kiểm tra Aggregator và luồng Quick Approve |

### Frontend (Flutter / GetX)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[NEW]** | `frontend/lib/modules/hologram_hub/views/widgets/company_pulse_bar.dart` | Widget dải nhịp đập doanh nghiệp trực quan |
| **[NEW]** | `frontend/lib/modules/hologram_hub/views/widgets/today_priority_list.dart` | Widget danh sách 1–3 việc ưu tiên hằng ngày |
| **[NEW]** | `frontend/lib/modules/hologram_hub/views/widgets/quick_approval_queue.dart` | Widget danh sách thẻ phê duyệt nhanh |
| **[NEW]** | `frontend/lib/modules/hologram_hub/views/widgets/active_missions_tracker.dart` | Widget theo dõi tiến độ các Mission đang chạy |
| **[NEW]** | `frontend/lib/modules/hologram_hub/views/widgets/cosa_quick_bar.dart` | Widget thanh lệnh nhanh kết nối Companion |
| **[MODIFY]** | `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` | Tái cấu trúc giao diện CEO Command Center sống động |
| **[MODIFY]** | `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` | Quản lý state, gọi API Aggregator, xử lý Quick Approve |

---

## 5. Tiêu Chí Nghiệm Thu Cho Phase P1 (Definition of Done)

1. **Hiệu Năng & Tốc Độ:**
   - `GET /hub/command-center` phản hồi dưới 100ms trên môi trường dev/staging.
2. **Tính Toàn Vẹn Dữ Liệu:**
   - Thao tác Quick Approve chuyển ngay trạng thái `approvals` sang `approved` và tạo bản ghi `outbox` tương ứng trong cùng một transaction.
   - Thao tác hoàn thành Task trên giao diện phản ánh ngay lập tức trên cơ sở dữ liệu.
3. **Trải Nghiệm Người Dùng (UX):**
   - Hologram Hub hiển thị đầy đủ 5 khu vực điều hành, giao diện tối ưu (Dark Theme sang trọng, micro-animations, màu sắc cảnh báo rõ ràng).
   - Bấm Approve trên thẻ duyệt ngay lập tức xóa thẻ đó khỏi hàng đợi trên UI với hiệu ứng mượt mà.
4. **Kiểm Thử Tự Động:**
   - 100% Pytest unit/integration tests mới cho Phase P1 đều **PASSED**.
   - `flutter analyze` đạt **0 lỗi/cảnh báo**.

---
*(Kế hoạch chi tiết Phase P1 đã được lưu trữ và đang ở trạng thái CHỜ BẠN XÁC NHẬN trước khi bắt đầu viết code).*
