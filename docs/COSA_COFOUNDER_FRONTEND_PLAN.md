# COSA CO-FOUNDER ARCHITECTURE (F4 SPEC)
## FRONTEND IMPLEMENTATION PLAN: FOUNDER COMMAND CENTER (FLUTTER)

> **Mục tiêu:** Tái cấu trúc Hologram Hub thành **Founder Command Center** chuyên nghiệp, trực quan, lấy **COSA Co-Founder** làm trung tâm điều hành, hiển thị **Company Pulse**, **Top 3 Focus (12WY)**, hàng đợi **Waiting for You (Decisions + Approvals)**, và chuyển danh sách Agent vào tab **AI Workforce & Packs Store**.

---

## 1. CẤU TRÚC GIAO DIỆN FOUNDER COMMAND CENTER

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 🌟 COSA FOUNDER COMMAND CENTER                                         │
├────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ 🤖 COSA CO-FOUNDER (AI Partner)                   [Ask COSA 💬]    │ │
│ │ "Chào Founder! 2/3 mục tiêu tuần đang đúng tiến độ.                │ │
│ │  Hôm nay có 1 quyết định chiến lược cần bạn chốt."                 │ │
│ │                                                                    │ │
│ │ 📊 COMPANY PULSE: [ 2 Goals OK ] [ 3 Missions ] [ 1 Decision ]     │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 🎯 TOP 3 FOCUS HÔM NAY (12-Week Year)                                 │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ 1. ⚠️ [DECISION] Quyết định ngân sách Marketing Ads (50tr vs 15tr)  │ │
│ │ 2. 🧪 [EXPERIMENT] Phỏng vấn 5 khách hàng kiểm chứng WTP            │ │
│ │ 3. 📋 [REVIEW] Rà soát Scoreboard tuần 3                            │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 📬 WAITING FOR YOU (Hàng đợi cần Founder xử lý)                       │
│ ┌───────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ ⚖️ STRATEGIC DECISIONS (1)    │ │ 🛡️ ACTION APPROVALS (2)          │ │
│ │ • Tăng ngân sách Marketing    │ │ • Phê duyệt gửi 50 Cold Emails   │ │
│ │   [Xem Phân tích Đa miền]     │ │ • Deploy Landing Page mới        │ │
│ │   [Chốt Quyết định]           │ │   [Approve]   [Reject]           │ │
│ └───────────────────────────────┘ └──────────────────────────────────┘ │
│                                                                        │
│ 🚀 ACTIVE MISSIONS (Nhiệm vụ Đa Agent)                                │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Mission: "Tìm 20 Khách hàng Trả tiền đầu tiên" [Progress: 65%]     │ │
│ │ • Marketing Agent: Hoàn thiện Landing Page (Done)                  │ │
│ │ • Sales Agent: Outreach 50 Leads (In Progress)                     │ │
│ │ • Tech Lead: Deploy Tracking Analytics (Done)                      │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 👥 [TAB] AI WORKFORCE (5 Core Domains & Optional Packs Store)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CÁC TỆP DỮ LIỆU & GIAO DIỆN CẦN TRIỂN KHAI

### A. Tầng Dữ liệu (Dart Models & API Client)
1. `frontend/lib/data/models/founder_decision_model.dart`:
   - `FounderDecisionModel`: `id`, `domain`, `question`, `contextSummary`, `options`, `aiRecommendation`, `evidenceIds`, `status`, `decisionMade`, `decidedAt`.
2. `frontend/lib/data/models/company_pulse_model.dart`:
   - `CompanyPulseModel`: `goalsOnTrack`, `totalActiveGoals`, `activeMissions`, `needsDecisionCount`, `pendingApprovalsCount`, `suggestedFocus`.
   - `NextBestActionModel`: `id`, `category`, `title`, `rationale`, `urgency`, `domain`.
3. `frontend/lib/data/models/workforce_pack_model.dart`:
   - `WorkforcePackModel`: `key`, `name`, `roleTitle`, `department`, `category` (`DOMAIN`, `OPTIONAL_DOMAIN`), `isActive`, `description`.
4. `frontend/lib/data/services/cofounder_api_service.dart`:
   - Gọi Backend API `/api/v1/cofounder/pulse`, `/api/v1/cofounder/top3`, `/api/v1/cofounder/chat`, `/api/v1/cofounder/decisions`, `/api/v1/workforce/packs`.

### B. Tầng Điều khiển (GetX Controller)
1. `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`:
   - Quản lý State của Pulse, Top 3 Focus, Waiting for You Queue, Active Missions, Packs.
   - Thao tác: `resolveDecision()`, `approveTask()`, `sendChatMessage()`, `toggleOptionalPack()`.

### C. Tầng Giao diện (Flutter Widgets)
1. `frontend/lib/modules/hologram_hub/widgets/cofounder_card_widget.dart`: Thẻ COSA Co-Founder AI Hero + Pulse Counters.
2. `frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart`: Widget danh sách Top 3 Focus theo 12 Week Year.
3. `frontend/lib/modules/hologram_hub/widgets/waiting_for_you_widget.dart`: Widget danh sách Decisions & Approvals chờ Founder.
4. `frontend/lib/modules/hologram_hub/widgets/decision_modal_sheet.dart`: BottomSheet / Dialog hiển thị phân tích chéo Marketing + Finance + Legal và lựa chọn chốt phương án.
5. `frontend/lib/modules/hologram_hub/widgets/ai_workforce_tab.dart`: Danh sách 5 Core Domains và Store bật/tắt Optional Packs.
6. `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`: Tích hợp các widgets trên thành giao diện Founder Command Center hoàn chỉnh.
