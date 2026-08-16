# Kế Hoạch Triển Khai Chi Tiết: Giai Đoạn P3 (Phase 3)
## Automation Gateway & Multi-Channel Adapters (Cổng Tự Động Hóa & Kênh Tương Tác)

> **Mục tiêu của Phase P3:**
> Xây dựng hệ thống giao tiếp đa kênh và cổng tự động hóa bền vững (**Durable Automation & Multi-Channel Runtime**):
> - **Durable Outbox & Retry Engine:** Quản lý toàn bộ hàng đợi phát tin ra ngoài (Email, Telegram, Zalo, Webhook) với cơ chế chống gửi trùng (`dedupe_key`), thử lại lũy tiến (Exponential Backoff), và trạng thái minh bạch.
> - **n8n Automation Gateway:** Đóng vai trò cầu nối điều phối các luồng tự động hóa mở rộng bên ngoài (n8n/Make/Webhook), hỗ trợ xác thực chữ ký HMAC SHA-256 hai chiều và xử lý Callbacks bất đồng bộ an toàn.
> - **Telegram & Zalo Channel Adapters:** Tiếp nhận tin nhắn từ người dùng bên ngoài qua Webhook công khai $\rightarrow$ Chuyển ngữ cảnh vào Brain $\rightarrow$ Phản hồi tự động hoặc soạn bản nháp tiếp cận.
> - **Chốt chặn an toàn (Approval Snapshot):** 100% tác vụ gửi tin diện rộng, chi tiền hoặc gọi automation có rủi ro cao từ AI Agent đều phải được Founder phê duyệt trên **CEO Command Center (Phase 1)** trước khi chuyển vào Outbox.

---

## 1. Cấu Trúc Kiến Trúc & Luồng Dữ Liệu Phase P3

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PHASE P3: AUTOMATION & CHANNEL GATEWAY                               │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│  [Public Telegram Webhook] ──┐                                   ┌──► [Telegram Bot API Client]        │
│                              ├──► [Inbound Channel Router] ──┐   │                                     │
│  [Public Zalo OA Webhook]  ──┘                               │   ├──► [Zalo OA / ZNS API Client]       │
│                                                              ▼   │                                     │
│  [Agent / Workflow Trigger] ──► [Policy & Approval] ──► [OUTBOX] ┼──► [Resend / Email API Client]      │
│                                                              ▲   │                                     │
│  [External n8n Callback]   ──► [HMAC Signature Check] ───────┘   └──► [n8n Automation Dispatcher]      │
│                                                                                                        │
└───────────────────────────────────────────────────▲────────────────────────────────────────────────────┘
                                                    │
┌───────────────────────────────────────────────────┴────────────────────────────────────────────────────┐
│                                   BACKEND: AutomationGatewayService (FastAPI)                          │
│  - OutboxProcessor: Quét hàng đợi outbox (pending), gửi tin qua Adapter tương ứng, xử lý retry/error   │
│  - n8nGateway: Dispatch job sang n8n Webhook, theo dõi run status, xác thực chữ ký callback             │
│  - TelegramAdapter: Xử lý tin nhắn đến/đi, format MarkdownV2, quản lý bot token theo Workspace         │
│  - ZaloAdapter: Xử lý webhook Zalo OA, xác thực MAC/Access Token, gửi tin ZNS và tin CSKH              │
└───────────────────────────────────────────────────▲────────────────────────────────────────────────────┘
                                                    │
        ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
        ▼                                           ▼                                           ▼
      outbox                                automation_runs &                           chatbots &
  (dedupe_key, status)                    automation_callbacks                      mcp_connections
```

---

## 2. Chi Tiết Các Nhiệm Vụ Kỹ Thuật Trong Phase P3

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TASK P3.1: Durable Outbox Engine & Worker Processor                             │
│ - Backend: Outbox Queue Processor xử lý gửi tin theo đợt (batch dispatch)      │
│ - Backend: Cơ chế chống gửi trùng lặp (dedupe_key) & Exponential Backoff Retry  │
│ - Backend: Ghi nhận log chi tiết vào outbox.error và audit_logs                 │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P3.2: n8n Automation Gateway & Signed Webhook Callbacks                    │
│ - Backend: Dispatch automation request sang n8n kèm HMAC-SHA256 Signature       │
│ - Backend: Public endpoint nhận callback POST /api/v1/public/automations/cb     │
│ - Backend: Quản lý vòng đời AutomationRun (running → succeeded / failed)        │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P3.3: Telegram Channel Adapter & Inbound Parser                            │
│ - Backend: Public Webhook POST /api/v1/public/channels/telegram/webhook/{ws_id} │
│ - Backend: Telegram Message Dispatcher (Text, Photo, Document, Keyboard)        │
│ - Backend: Test Connection Bot Token trực tiếp từ giao diện Admin               │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P3.4: Zalo Channel Adapter & OA Integration                                │
│ - Backend: Public Webhook POST /api/v1/public/channels/zalo/webhook/{ws_id}     │
│ - Backend: Zalo OA API Client gửi tin nhắn tư vấn và tin ZNS                    │
│ - Backend: Quản lý Refresh Token & Session kết nối an toàn                      │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P3.5: Frontend Automation Console & Channel Manager UI                     │
│ - Frontend: Quản lý trạng thái kết nối các kênh (Telegram, Zalo, n8n, Resend)   │
│ - Frontend: Bảng theo dõi hàng đợi Outbox thời gian thực (Status, Retries, Logs)│
│ - Frontend: Nút Test Connection kiểm tra phản hồi trực tiếp từ nhà cung cấp     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Đặc Tả Dữ Liệu API Contract (Backend $\leftrightarrow$ Frontend $\leftrightarrow$ External)

### 3.1 Durable Outbox & Queue Monitoring
- `GET /api/v1/workspaces/{workspace_id}/outbox` $\rightarrow$ Lấy danh sách hàng đợi gửi tin (kèm bộ lọc status: `pending`, `sent`, `failed`).
- `POST /api/v1/workspaces/{workspace_id}/outbox/{outbox_id}/retry` $\rightarrow$ Thử gửi lại ngay lập tức một bản ghi lỗi.
- `POST /api/v1/workspaces/{workspace_id}/outbox/process-batch` $\rightarrow$ Kích hoạt worker xử lý nhanh hàng đợi.

### 3.2 n8n Automation Gateway
- `GET /api/v1/workspaces/{workspace_id}/automations/definitions` $\rightarrow$ Danh sách các automation đã cấu hình.
- `POST /api/v1/workspaces/{workspace_id}/automations/dispatch` $\rightarrow$ Kích hoạt chạy một workflow n8n:
```json
{
  "automation_key": "sync_crm_to_sheets",
  "payload": {
    "lead_id": "900112233445566778",
    "lead_name": "Nguyễn Văn A",
    "company": "Công ty ABC"
  }
}
```
- `POST /api/v1/public/automations/callback/{run_id}` **(Public Callback with HMAC)**:
  - Header: `X-COSA-Signature: sha256=...`
  - Body:
```json
{
  "provider_execution_id": "n8n_exec_987654",
  "status": "succeeded",
  "result": {
    "sheet_row_id": 42,
    "synced_at": "2026-08-16T11:00:00Z"
  }
}
```

### 3.3 Telegram Channel Webhook & Sender
- `POST /api/v1/public/channels/telegram/webhook/{workspace_id}` **(Public Webhook from Telegram Server)**:
  - Nhận update chuẩn của Telegram Bot API (`message`, `callback_query`).
- `POST /api/v1/workspaces/{workspace_id}/channels/telegram/test` $\rightarrow$ Gửi tin nhắn test kiểm tra bot token.

### 3.4 Zalo Channel Webhook & Sender
- `POST /api/v1/public/channels/zalo/webhook/{workspace_id}` **(Public Webhook from Zalo Server)**:
  - Nhận event từ Zalo OA (`user_send_text_message`, `oa_send_text_message`).
- `POST /api/v1/workspaces/{workspace_id}/channels/zalo/test` $\rightarrow$ Kiểm tra kết nối Zalo OA App Secret & Access Token.

---

## 4. Danh Sách Files Cần Tạo Mới & Chỉnh Sửa Trong Phase P3

### Backend (FastAPI / Outbox Runtime)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[NEW]** | `backend/app/modules/integrations/outbox_processor.py` | Engine xử lý quét hàng đợi Outbox, điều phối gửi Telegram/Zalo/Email với Retry |
| **[NEW]** | `backend/app/modules/integrations/telegram_adapter.py` | Adapter giao tiếp Telegram Bot API (gửi tin, parse inbound update) |
| **[NEW]** | `backend/app/modules/integrations/zalo_adapter.py` | Adapter giao tiếp Zalo OA & ZNS (gửi tin, parse webhook, token refresh) |
| **[NEW]** | `backend/app/modules/integrations/n8n_gateway_service.py` | Service điều phối n8n workflow, ký HMAC và xử lý callbacks |
| **[NEW]** | `backend/app/modules/integrations/public_channel_router.py` | Router tiếp nhận webhooks công khai từ Telegram, Zalo và n8n |
| **[NEW]** | `backend/app/modules/integrations/outbox_router.py` | Router REST API quản lý và theo dõi Outbox Queue |
| **[MODIFY]** | `backend/app/main.py` | Đăng ký `outbox_router` và `public_channel_router` |
| **[NEW]** | `backend/app/tests/test_p3_automation_gateway.py` | Pytest kiểm thử Outbox Processor, n8n HMAC, Telegram & Zalo adapters |

### Frontend (Flutter / GetX)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[NEW]** | `frontend/lib/data/services/outbox_service.dart` | Service kết nối API quản trị Outbox & Automation Gateway |
| **[NEW]** | `frontend/lib/modules/channels/views/widgets/outbox_queue_monitor.dart` | Widget theo dõi danh sách Outbox thời gian thực kèm nút Retry |
| **[NEW]** | `frontend/lib/modules/channels/views/widgets/channel_connection_card.dart` | Thẻ cấu hình & kiểm tra trạng thái kết nối Telegram/Zalo/n8n |
| **[MODIFY]** | `frontend/lib/modules/channels/controllers/channels_controller.dart` | Controller quản lý trạng thái kết nối kênh và hàng đợi Outbox |
| **[MODIFY]** | `frontend/lib/modules/channels/views/channels_view.dart` | Tích hợp giao diện quản lý Gateway & Outbox tập trung |

---

## 5. Tiêu Chí Nghiệm Thu Cho Phase P3 (Definition of Done)

1. **Outbox Gửi Tin An Toàn & Chống Trùng:**
   - Khi một tác vụ gửi tin được tạo vào `Outbox`, `dedupe_key` ngăn chặn hoàn toàn việc nhân bản tin nhắn.
   - Khi gặp sự cố mạng (network failure), worker tự động tăng số lần thử (`attempts`) và lên lịch thử lại theo lũy tiến.
2. **Xác Thực Bảo Mật n8n Callback:**
   - Callback từ n8n được kiểm tra chữ ký HMAC SHA-256; từ chối (401/403) mọi yêu cầu có chữ ký không hợp lệ.
3. **Telegram & Zalo Hoạt Động Liền Mạch:**
   - Kiểm tra kết nối Bot Token trả về tên Bot và trạng thái `ACTIVE` tức thì.
   - Nhận tin nhắn inbound qua webhook phân tích đúng người gửi và nội dung.
4. **Kiểm Thử Tự Động:**
   - 100% Pytest unit/integration tests cho Phase P3 **PASSED**.
   - `flutter analyze` đạt **0 lỗi, 0 cảnh báo**.

---
*(Kế hoạch chi tiết Phase P3 đã được lưu trữ tại `docs/PHASE_3_DETAILED_IMPLEMENTATION_PLAN.md` và sẵn sàng để triển khai code khi bạn yêu cầu).*
