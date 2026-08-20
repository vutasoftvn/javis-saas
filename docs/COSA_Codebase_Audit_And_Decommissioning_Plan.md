# BÁO CÁO PHÂN TÍCH, ĐỐI CHIẾU VÀ ĐỀ XUẤT TÁI CẤU TRÚC CODEBASE COSA
## (COSA CODEBASE AUDIT, DECOMMISSIONING & RECONFIGURATION PLAN)

> **Tài liệu tham chiếu chuẩn:**
> - [COSA_Comprehensive_Refactoring_Plan_Backend_Frontend.md](file:///Volumes/SSD/javis-saas/docs/COSA_Comprehensive_Refactoring_Plan_Backend_Frontend.md)
> - [CLAUDE.md](file:///Volumes/SSD/javis-saas/CLAUDE.md)
> - [markdown/Structure.md](file:///Volumes/SSD/javis-saas/markdown/Structure.md)
> - Trạng thái: **Đề xuất Kế hoạch (Audit & Planning Phase - Không sửa code)**
> - Ngày lập: 2026-08-20

---

## 1. TỔNG QUAN KẾT QUẢ ĐỐI CHIẾU VỚI PHASES 0-9

Sau khi hoàn thành 10 phases tái cấu trúc kiến trúc lõi (Phase 0 đến Phase 9), codebase COSA hiện tại có hai mảng song song:
1. **Kiến trúc mới chuẩn mực (Target Architecture):**
   - Core Contracts & Business Core độc lập 100% với AI (Phase 1).
   - Event Store SQLite append-only, Session Fork/Replay (Phase 2).
   - Intent Router chặn greeting, Context Budget Engine (Phase 3).
   - Central Tool Registry & Presenters (Phase 4).
   - Skills & Workflows tách rời dạng Declarative (Phase 5).
   - Declarative Agent Profiles trong One Runtime (Phase 6).
   - Multi-LLM Adapters & OpenSandbox Execution (Phase 7).
   - Hologram Hub 3-Pane Responsive với AdaptiveScaffold (Phase 8).
   - Bộ kiểm thử E2E 100% Passed (Phase 9).

2. **Các thành phần tồn dư, rác và cấu hình chưa đồng bộ cần xử lý:**
   - **Backend:** Thư mục `app/workforce/agents/` cũ chứa nhiều lớp monolith trùng lặp với `app/workforce/` mới; các router dead/unmounted; các scripts và test DSPy thử nghiệm cũ.
   - **Frontend:** 37 thư mục module trong đó hơn 20 thư mục chỉ là dummy scaffold tự sinh (Text '... đã sẵn sàng'), chưa được nối vào router `app_pages.dart` và làm rối cấu trúc thư mục.
   - **Cấu hình & Root:** Docker compose còn dùng tiền tố cũ `javis_` và biến môi trường không dùng; root chứa ảnh chụp màn hình và thư mục backup.

---

## 2. MA TRẬN PHÂN LOẠI HÀNH ĐỘNG CHO TỪNG THÀNH PHẦN

### 2.1. BACKEND: Chi tiết Xoá / Hợp nhất / Cập nhật

| Thành phần | Đường dẫn | Phân loại | Lý do & Phương án chi tiết |
| :--- | :--- | :--- | :--- |
| **Monolithic Domain Agents** | `backend/app/workforce/agents/domains/` (`marketing/`, `sales/`, `finance/`, `legal/`, `learning/`) | 🗑️ **XOÁ** | Các class agent riêng lẻ này vi phạm trực tiếp nguyên tắc "One Runtime — Declarative Profiles" (CLAUDE §3, §4). Toàn bộ profile đã được khai báo qua `workforce/registry/defaults.py` và logic nghiệp vụ thuần tuý nằm trong `app/business/`. |
| **Skills Library cũ** | `backend/app/workforce/agents/skills_library/` | 🗑️ **XOÁ** | Trùng lặp hoàn toàn với hệ thống `backend/app/workforce/skills/` chuẩn hóa trong Phase 5. |
| **ADK / LangGraph Runtime cũ** | `backend/app/workforce/agents/adk_runtime/` (`legacy_sales_pilot.py`, `sales_graph.py`) | 🗑️ **XOÁ** | Dead code từ giai đoạn POC ban đầu, không còn phục vụ trong kiến trúc One Runtime. |
| **DeepSeek Harness cũ** | `backend/app/workforce/agents/runtime/adapters/deepseek_harness.py` | 🔀 **MIGRATE** | Chuyển các utility format hữu ích sang `workforce/adapters/deepseek_adapter.py` rồi xoá folder `agents/runtime/adapters/`. |
| **Orchestration cũ** | `backend/app/workforce/agents/orchestration/` (`chief_of_staff.py`, `mission_control_bus.py`) & `agents/orchestrator/` | 🔀 **HỢP NHẤT** | Chuyển listener của mission bus sang `workforce/dispatcher/` hoặc `core/events.py`. Toàn bộ vai trò Co-founder đã được đảm nhiệm bởi `workforce/orchestrator/cosa_cofounder_service.py`. |
| **Governance phân mảnh** | `backend/app/workforce/agents/governance/` | 🔀 **HỢP NHẤT** | Gộp các model còn thiếu vào `backend/app/workforce/governance/` và xoá folder cũ. |
| **Gateway Router đóng gói cũ** | `backend/app/workforce/agents/gateway/` | 🗑️ **XOÁ** | Router gom 8 sub-router chưa từng được mount trực tiếp vào `main.py`. |
| **Capabilities Router** | `backend/app/workforce/agents/capabilities/router.py` | 🔄 **CẬP NHẬT** | Di chuyển sang `backend/app/workforce/capabilities/router.py` và cập nhật import trong `main.py`. |
| **Duplicate Workforce Router** | `backend/app/workforce/router.py` | 🔄 **CẬP NHẬT** | Xoá duplicate route prefix `/api/v1/agent-platform`, giữ duy nhất `/api/v1/workforce`. |
| **DSPy / ADK Legacy Tests** | `backend/app/tests/test_dspy_*.py` (7 files), `test_zalo_mcp.py` | 🗑️ **XOÁ** | Các file test framework cũ không còn nằm trong kiến trúc mục tiêu. |
| **Scripts Chẩn đoán & Quét Tool** | `backend/app/scripts/cosa_doctor.py`, `ai_tools_report.py` | 🔄 **CẬP NHẬT** | Nâng cấp để tương thích với `ToolRegistry` mới và kiểm tra sức khoẻ Event Store SQLite / Multi-LLM Gateway. |

---

### 2.2. FRONTEND: Chi tiết Xoá / Hợp nhất / Cập nhật

| Thành phần | Đường dẫn | Phân loại | Lý do & Phương án chi tiết |
| :--- | :--- | :--- | :--- |
| **10 Core Business Modules** | `modules/` (`hologram_hub`, `auth`, `dashboard`, `tasks`, `strategy`, `marketing`, `sales`, `finance`, `legal`, `settings`) | 🛡️ **GIỮ & CHUẨN HOÁ** | Là các màn hình nghiệp vụ thực tế của Founder OS. Cần tiếp tục chuẩn hóa theo 3 tầng (Data/Domain/Presentation). |
| **4 Hub Extensions** | `modules/` (`approvals`, `vault`, `workflows`, `skills`) | 🔀 **TÍCH HỢP** | Tích hợp làm tab, modal hoặc inspector pane trong `hologram_hub` thay vì để làm module độc lập rời rạc. |
| **Chat Module cũ 1-cột** | `modules/chat/` | 🗑️ **XOÁ** | Trải nghiệm trò chuyện và streaming tool calling đã chuyển sang `center_workspace_pane.dart` trong Hologram Hub. |
| **22 Dummy Scaffold Modules** | `modules/` (`backup`, `branding`, `chatbots`, `connections`, `developer`, `diagnostics`, `graph`, `plugins`, `prompts`, `realtime_voice`, `tech`, `tech_radar`, `usage`, `organization`, `mission_control`, `ai_operations`, `ai_team`, `channels`, `business_packs`, `audit`, `runtime`, `governance`) | 🗑️ **XOÁ HOÀN TOÀN** | Các module tự sinh chỉ chứa text placeholder rỗng, không có logic thực và không được mount trong `AppPages.routes`. Xoá để làm gọn cây thư mục frontend từ 37 xuống 10 modules cốt lõi. |
| **Routing & Navigation** | `frontend/lib/core/routing/` (`app_pages.dart`, `app_routes.dart`) | 🔄 **CẬP NHẬT** | Khai báo lại danh mục routes chính xác, dọn dẹp các route thừa, thiết lập `HologramHubScreen` làm trung tâm điều hành. |
| **Màn hình Responsive** | Toàn bộ Core Views | 🔄 **CẬP NHẬT** | Bọc toàn bộ các view lớn bằng `AdaptiveScaffold` và `ResponsiveLayoutBuilder` từ Phase 8. |

---

### 2.3. CẤU HÌNH, SCRIPTS & HẠ TẦNG: Chi tiết Xoá / Cập nhật

| Thành phần | Đường dẫn | Phân loại | Lý do & Phương án chi tiết |
| :--- | :--- | :--- | :--- |
| **Docker Compose** | `docker-compose.yml` | 🔄 **CẬP NHẬT** | Chuẩn hóa prefix container thành `cosa_*` (`cosa_postgres`, `cosa_minio`, `cosa_brain_api`, `cosa_agent_worker`, `cosa_opensandbox`). Xoá các biến provider thừa (`CHAT_DEFAULT_PROVIDER=kira_ai`, `PROVIDER_CONFIGURED_KIRAAI`). Cấu hình đúng `MultiLLMGateway` keys. |
| **CLI Điều hành** | `cosa.sh` | 🔄 **CẬP NHẬT** | Cập nhật lệnh `doctor`, `status`, `backup` để khớp với container names và scripts mới. |
| **Build & Test Automation** | `Makefile` | 🔄 **CẬP NHẬT** | Thêm các target `test-backend`, `test-frontend`, `clean`, `doctor`. |
| **Root Scratch & Media** | `home.png`, `image.png` | 🔀 **DI CHUYỂN** | Chuyển vào `docs/assets/` để giữ thư mục gốc sạch sẽ. |
| **Root Backups cũ** | `backups/` | 🗑️ **XOÁ** | Dữ liệu cũ đã được lưu trữ trong Git history. |
| **Tài liệu đặc tả cũ** | `myiris.md`, `mCOSA_V13_Focused_Company_Cycle_OS_...md` | 🔀 **DI CHUYỂN** | Chuyển vào `docs/architecture/legacy_specs/` để lưu vết tài liệu lịch sử. |

---

## 3. LỘ TRÌNH ĐỀ XUẤT THỰC HIỆN DỌN DẸP & TÁI CẤU HÌNH

```text
Giai đoạn 1: Dọn dẹp Thư mục Gốc & Tài liệu Lưu trữ (Root Cleanup)
Giai đoạn 2: Tái cấu trúc & Hợp nhất Workforce Backend (Xóa app/workforce/agents/ redundant)
Giai đoạn 3: Tinh gọn Frontend Modules (Xóa 22 Dummy Modules & Chuẩn hóa Router AppPages)
Giai đoạn 4: Đồng bộ Cấu hình Hạ tầng (docker-compose, cosa.sh, Makefile, .env.example)
Giai đoạn 5: Chạy Kiểm thử Toàn diện (Verify Zero Regression 47/47 Tests Passed)
```

---

## 4. TIÊU CHUẨN NGHIỆM THU HOÀN TẤT DỌN DẸP

1. **Backend:**
   - Cây thư mục `app/workforce/` chỉ còn 1 cấu trúc chuẩn duy nhất (`adapters`, `capabilities`, `chat`, `dispatcher`, `governance`, `orchestrator`, `registry`, `skills`, `tools`).
   - AST Scanner xác nhận 0% import lỗi và 0% import từ thư mục cũ.
2. **Frontend:**
   - Cây thư mục `lib/modules/` giảm từ 37 xuống đúng 10 Core Modules sạch sẽ.
   - `AppPages.routes` phản ánh chính xác 100% màn hình thực tế.
   - Toàn bộ Widget tests và Responsive Layout chạy mượt mà.
3. **Chất lượng tổng thể:**
   - Toàn bộ 47/47 tests (Backend Pytest + Frontend Flutter) tiếp tục đạt **100% Passed**.
