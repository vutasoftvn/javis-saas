# COSA CO-FOUNDER ARCHITECTURE (F4 SPEC)
## PHASE 2 IMPLEMENTATION PLAN: BACKEND CO-FOUNDER ENGINE & INTENT ROUTING

> **Mục tiêu:** Xây dựng tầng trí tuệ và điều phối trung tâm **COSA Co-Founder Service**, trang bị các capabilities cốt lõi: Phản biện dựa trên Bằng chứng (`Challenge Mode`), Tổng hợp đa miền (`Cross-domain Synthesis`), Đề xuất hành động tốt nhất (`Next Best Action`), và Phân loại ý định Founder (`Intent Router`).

---

## 1. PHÂN TÍCH KIẾN TRÚC & CAPABILITIES (F4 SPECIFICATION)

```text
                                HUMAN FOUNDER
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │      COSA CO-FOUNDER      │
                        │  (CosaCofounderService)   │
                        └─────────────┬─────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           ▼                          ▼                          ▼
   Context Resolver           Challenge Engine           Synthesis Engine
 (Minimum Context Only)    (Evidence-Driven F1/F3)    (Cross-Domain Cross-Check)
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      ▼
                                INTENT ROUTER
        ┌───────────────────┬─────────┴─────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼
    GREETING         FOUNDER_REVIEW      FOUNDER_DECISION    FOUNDER_COMMAND
(Friendly Chat,    (Top 3 Focus, 12WY,   (Cross-domain ROI,   (Goal Shaping &
 No Heavy DB Load)   Overdue, Risks)       Cashflow Runway)   Mission Dispatch)
```

---

## 2. CHI TIẾT CÁC THÀNH PHẦN CẦN XÂY DỰNG

### 2.1. Nâng cấp Intent Router (`backend/app/workforce/routing/`)
- **Vấn đề hiện tại:** Router cũ chỉ map từ khóa thô sơ sang các con bot (`sales`, `finance`, `marketing`, `founder`, `google_search`).
- **Nâng cấp mới theo Mục 32-33 trong F4:**
  - `GREETING`: Chào hỏi thông thường (ví dụ: *"Chào COSA"*, *"Hello"*) $\rightarrow$ Phản hồi tự nhiên, KHÔNG load project database.
  - `FOUNDER_REVIEW`: Yêu cầu rà soát ưu tiên (ví dụ: *"Hôm nay tôi nên làm gì?"*, *"Tuần này nên tập trung gì?"*) $\rightarrow$ Kích hoạt `get_next_best_action()` trả về Top 3.
  - `FOUNDER_DECISION`: Tham vấn quyết định (ví dụ: *"Có nên tăng ngân sách ads lên 50 triệu?"*) $\rightarrow$ Kích hoạt `synthesize_cross_domain()` kết hợp Marketing + Finance.
  - `FOUNDER_REFLECTION`: Chia sẻ băn khoăn, định hướng chiến lược.
  - `FOUNDER_COMMAND`: Giao mục tiêu lớn (ví dụ: *"Trong 30 ngày tìm 20 khách hàng trả tiền"*) $\rightarrow$ Kích hoạt `goal_shaping` và tạo Mission.
  - `DOMAIN_TASK`: Các yêu cầu thực thi cụ thể thuộc 1 domain (Sales, Tech, Legal...).

---

### 2.2. Xây dựng `CosaCofounderService` (`backend/app/workforce/orchestrator/cosa_cofounder_service.py`)

Service trung tâm chịu trách nhiệm:

1. **System Prompt Chuẩn hóa (Mục 53 F4):**
   - Đóng vai trò Co-Founder thông minh, thẳng thắn, luôn phân biệt rõ **Fact vs Assumption vs Evidence**.
   - Tối ưu cho tiến độ kinh doanh thực tế (`Business Progress`), không chỉ hoàn thành task đơn thuần (`Task Completion`).
   - Tôn trọng quyền quyết định tối cao của Human Founder.

2. **Context Retrieval tối thiểu (`retrieve_minimum_viable_context`):**
   - Không load toàn bộ database CRM, sổ kế toán hay kho văn bản.
   - Chỉ truy xuất đúng những dữ liệu thiết yếu: Active Goals, 12 Week Year Scoreboard, Tasks quá hạn, Active Missions, Pending Decisions & Approvals, Rủi ro nghiêm trọng.

3. **Challenge Mode (`challenge_assumptions`):**
   - Đối chiếu yêu cầu của Founder với kho Evidence hiện có (kết nối F1/F2/F3 Problem-First).
   - Nếu phát hiện giả định chưa kiểm chứng: Đề xuất phương án kiểm chứng trước khi build/tiêu tiền.

4. **Cross-Domain Business Synthesis (`synthesize_cross_domain`):**
   - Ví dụ: Khi Marketing đề xuất chi tiêu, tự động truy vấn Cashflow Runway từ Finance và đánh giá rủi ro pháp lý nếu có.

5. **Next Best Action Engine (`get_next_best_action`):**
   - Tổng hợp Top 3 hành động quan trọng nhất trong ngày dựa trên chiến thuật tuần (Weekly Tactics) và điểm nghẽn thực tế.

---

### 2.3. Xây dựng Co-Founder REST APIs (`backend/app/workforce/api/cofounder_api.py`)

Cung cấp các endpoints cho Frontend Flutter:
- `POST /api/v1/cofounder/chat`: Giao tiếp hội thoại và nhận chỉ đạo từ Founder.
- `GET /api/v1/cofounder/pulse`: Lấy nhịp tim doanh nghiệp (Company Pulse): Số goals đúng hạn, Missions đang chạy, Số quyết định đang chờ, Rủi ro lớn.
- `GET /api/v1/cofounder/top3`: Lấy danh sách Top 3 Suggested Focus hôm nay.
- `POST /api/v1/cofounder/decisions`: Tạo hoặc truy vấn các bài toán quyết định chiến lược.
- `POST /api/v1/cofounder/decisions/{id}/resolve`: Founder chốt quyết định.

---

## 3. CÁC BƯỚC TRIỂN KHAI CHI TIẾT (STEP-BY-STEP)

### Bước 1: Nâng cấp Intent Router & Enums
- Chỉnh sửa [backend/app/workforce/routing/deterministic.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/routing/deterministic.py) và [backend/app/workforce/routing/router.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/routing/router.py):
  - Bổ sung `FOUNDER_REVIEW`, `FOUNDER_DECISION`, `FOUNDER_COMMAND`, `FOUNDER_REFLECTION`.
  - Tối ưu rule-based và deterministic check.

### Bước 2: Xây dựng `CosaCofounderService`
- Tạo file `backend/app/workforce/orchestrator/cosa_cofounder_service.py`:
  - Cài đặt COSA System Prompt.
  - Cài đặt các method: `handle_message()`, `challenge_assumptions()`, `synthesize_cross_domain()`, `get_next_best_action()`, `get_company_pulse()`.

### Bước 3: Xây dựng Co-Founder API Router & Schemas
- Tạo file `backend/app/workforce/api/cofounder_api.py`.
- Đăng ký router vào `backend/app/main.py`.

### Bước 4: Viết Unit Tests & Acceptance Verification cho Phase 2
- Tạo file `backend/app/tests/workforce/test_phase2_cofounder_engine.py`:
  - **Test 1 (Greeting):** Gửi *"Chào COSA"* $\rightarrow$ Nhận phản hồi trò chuyện thân thiện, không gọi DB nặng.
  - **Test 2 (Morning Routine / Top 3):** Gửi *"Hôm nay tôi nên làm gì?"* $\rightarrow$ Kích hoạt `FOUNDER_REVIEW`, trả về Top 3 Next Best Actions.
  - **Test 3 (Challenge Mode):** Founder đưa ra ý tưởng chưa có bằng chứng $\rightarrow$ COSA phản biện và đề xuất kiểm chứng trước.
  - **Test 4 (Cross-domain Synthesis):** Gửi câu hỏi về tăng ngân sách $\rightarrow$ COSA kết hợp Marketing + Finance đưa ra khuyến nghị đa chiều.

---

## 4. CHECKLIST NGHIỆM THU PHASE 2

- [ ] `IntentRouter` nhận diện chính xác các câu hỏi Founder (`Greeting`, `Review`, `Decision`, `Command`).
- [ ] `CosaCofounderService.get_company_pulse()` trả về đúng thống kê Goals, Missions, Decisions, Risks.
- [ ] `CosaCofounderService.get_next_best_action()` trả về đúng Top 3 đề xuất.
- [ ] `challenge_assumptions()` hoạt động chính xác theo nguyên tắc Evidence-driven F1/F2/F3.
- [ ] API endpoints `/api/v1/cofounder/*` chạy mượt mà và được bảo vệ bằng auth.
- [ ] Toàn bộ unit tests của Phase 2 pass 100%.
