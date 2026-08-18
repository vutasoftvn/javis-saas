# KẾ HOẠCH TRIỂN KHAI CHI TIẾT — PHASE 1: STAGE FOUNDATION
## Nền Tảng Phân Định Giai Đoạn & Động Cơ Chính Sách Quản Trị COSA (Full-Stack Backend + Frontend)

**Mục tiêu của Phase 1:** Thiết lập toàn bộ hạ tầng nhận thức Stage ở cả 2 tầng **Backend & Frontend Flutter**, phân tách rạch ròi giữa **Company State** (Bản sắc, danh mục) và **Project State** (Vòng đời 7 Stage thực tế), đồng thời cung cấp `ManagementPolicyEngine` làm kim chỉ nam chính sách và các UI components hiển thị Stage đầu tiên trên giao diện Hologram Hub.

---

## 1. TỔNG QUAN KIẾN TRÚC PHASE 1 (FULL-STACK)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FLUTTER FRONTEND (GETX)                         │
│  - StageBadge Widget (Gradient Colors S0 - S6)                         │
│  - StageSelectorHeader (Dropdown Project + Current Stage Badge)        │
│  - StagePolicyDialog (Bảng tra cứu quy chuẩn & mục tiêu Stage)         │
│  - StageService & HologramHubController State                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST API
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (CORE)                         │
│  - StageFoundationRouter (/api/v1/founder/stage/...)                   │
│  - StageResolverService (Company Identity + Project Stage)             │
│  - ManagementPolicyEngine (Chính sách chuẩn S0 - S6)                   │
│  - SQLAlchemy Models (Project.project_stage, Workspace.company_stage)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CHI TIẾT TRIỂN KHAI BACKEND

### 2.1. Database Models (`backend/app/founder_os/strategy/models.py` & `backend/app/platform/auth/models.py`)

#### 1. Cập nhật model `Project` (`backend/app/founder_os/strategy/models.py`):
```python
class Project(Base):
    __tablename__ = "projects"
    
    # ... Giữ nguyên toàn bộ các trường hiện có ...
    
    # --- STAGE-AWARE FIELDS MỚI ---
    project_stage: Mapped[str] = mapped_column(
        String(50), 
        default="S1_PROBLEM_VALIDATION", 
        index=True
    )  # S0_EXPLORE, S1_PROBLEM_VALIDATION, S2_SOLUTION_VALIDATION, S3_BUSINESS_VALIDATION, S4_GO_TO_MARKET, S5_OPERATE_GROWTH, S6_SCALE_GOVERN
    
    stage_started_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    
    stage_goal: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True
    )  # Mục tiêu tối thượng của Stage hiện tại
    
    critical_constraints: Mapped[dict] = mapped_column(
        JSONB, 
        default=list
    )  # List[str]: Các rào cản, điểm nghẽn rủi ro lớn nhất
    
    exit_criteria_jsonb: Mapped[dict] = mapped_column(
        JSONB, 
        default=dict
    )  # Tiêu chí chuẩn cần đạt để chuyển sang stage kế tiếp
    
    stage_metadata: Mapped[dict] = mapped_column(
        JSONB, 
        default=dict
    )  # Snapshot lịch sử, ghi chú chuyển giai đoạn, confidence
```

#### 2. Cập nhật model `Workspace` (`backend/app/platform/auth/models.py`):
```python
class Workspace(SnowflakeIDMixin, Base):
    __tablename__ = "workspaces"
    
    # ... Giữ nguyên các trường name, created_at ...
    company_stage: Mapped[str] = mapped_column(
        String(50), 
        default="S5_OPERATE_GROWTH"
    )
```

---

### 2.2. Schemas & Enums (`backend/app/founder_os/strategy/schemas/stage_schemas.py`) [NEW]
* Định nghĩa Enum `ProjectStageEnum` (S0..S6).
* Định nghĩa Pydantic Schemas:
  - `StagePolicySpec`: Quy cách chính sách (Goal, Questions, Required Entities, Metrics, Deemphasized Tools, Priority Agents).
  - `StageContextResponse`: Ngữ cảnh tổng hợp (Company Identity + Project Stage + Policy).
  - `ProjectStageUpdateRequest`: Request body cập nhật Stage, Goal, Constraints.

---

### 2.3. Services Layer (Backend)

#### 1. `StageResolverService` (`backend/app/founder_os/strategy/services/stage_resolver_service.py`) [NEW]
* Phân giải ngữ cảnh: Nạp Company Identity (Vision, Mission, Core Values từ `StrategyFoundation`) + Project Stage.
* Fallback thông minh: Nếu không có `project_id`, tự động chọn Project P0 active hoặc trả về Company Context.

#### 2. `ManagementPolicyEngine` (`backend/app/founder_os/strategy/services/management_policy_engine.py`) [NEW]
* Từ điển chính sách chuẩn cho toàn bộ **7 Stage (S0 → S6)**:
  - **S0 (Explore):** Goal: Khám phá cơ hội | Tắt: BSC, NPS, CRM, SOP | Bật: Assumption Map, PESTEL-lite | Agent: Research, Customer.
  - **S1 (Problem Validation):** Goal: Xác thực ICP & Nỗi đau | Tắt: BSC, NPS, CRM, Ads | Bật: Customer Discovery, Learning OKR | Agent: Customer, Research.
  - **S2 (Solution Validation):** Goal: Xác thực Giải pháp & Trả tiền | Tắt: BSC, Org OKRs | Bật: MVP Spec, Pricing Test, Validation OKR | Agent: Product, Customer, Tech.
  - **S3 (Business Validation):** Goal: Xác thực Unit Economics & Bán hàng | Tắt: BSC, Heavy SOP | Bật: Unit Economics, Evidence-backed SWOT | Agent: Finance, Sales, Product.
  - **S4 (Go-to-Market):** Goal: Kênh tiếp cận lặp lại | Tắt: BSC tổng thể | Bật: Sales Funnel, CRM Pipeline, TOWS Options | Agent: Marketing, Sales, Finance.
  - **S5 (Operate & Grow):** Goal: Vận hành ổn định & Lợi nhuận | Bật toàn bộ: 12WY, OKRs, Company Health (BSC Lens), SOPs, AI Workforce | Agent: Execution, Finance, Tech.
  - **S6 (Scale & Govern):** Goal: Mở rộng quy mô & Quản trị rủi ro | Bật: Portfolio Matrix, Governance, Strategy Balance (BSC), Risk Register | Agent: Execution, Legal, Finance.

---

### 2.4. API Router Layer (`backend/app/founder_os/strategy/routers/stage_foundation_router.py`) [NEW]
* `GET /api/v1/founder/stage/context`: Lấy Context tổng hợp (kèm query param `project_id`).
* `GET /api/v1/founder/stage/policy/{stage}`: Lấy chi tiết chính sách của một Stage.
* `PATCH /api/v1/founder/stage/project/{project_id}`: Cập nhật Stage, Goal, Constraints của Project.
* `GET /api/v1/founder/stage/list-stages`: Lấy danh sách 7 Stage chuẩn và tóm tắt.
* Đăng ký router vào `backend/app/founder_os/strategy/router.py`.

---

## 3. CHI TIẾT TRIỂN KHAI FRONTEND (FLUTTER)

### 3.1. Data Models & Enums (`frontend/lib/data/models/stage_model.dart`) [NEW]
* `enum ProjectStage`:
  - `s0Explore` ("S0 — Explore", màu Slate/Xám `#64748B`, icon `Icons.explore_outlined`)
  - `s1ProblemValidation` ("S1 — Problem Validation", màu Indigo `#6366F1`, icon `Icons.psychology_outlined`)
  - `s2SolutionValidation` ("S2 — Solution Validation", màu Purple `#A855F7`, icon `Icons.lightbulb_outlined`)
  - `s3BusinessValidation` ("S3 — Business Validation", màu Amber `#F59E0B`, icon `Icons.attach_money_outlined`)
  - `s4GoToMarket` ("S4 — Go-to-Market", màu Cyan/Teal `#06B6D4`, icon `Icons.campaign_outlined`)
  - `s5OperateGrowth` ("S5 — Operate & Grow", màu Emerald Green `#10B981`, icon `Icons.trending_up_outlined`)
  - `s6ScaleGovern` ("S6 — Scale & Govern", màu Crimson/Red `#EF4444`, icon `Icons.account_balance_outlined`)
* `StagePolicyModel`: Chứa `primaryGoal`, `primaryQuestions`, `recommendedMethods`, `deemphasizedTools`, `priorityAgents`.
* `StageContextModel`: Chứa thông tin Project, Company, Stage và Policy tương ứng.

---

### 3.2. Data Service Layer (`frontend/lib/data/services/stage_service.dart`) [NEW]
* Gọi API Backend:
  - `Future<StageContextModel?> getStageContext({int? projectId})`
  - `Future<StagePolicyModel?> getStagePolicy(String stage)`
  - `Future<List<Map<String, dynamic>>> listAllStages()`
  - `Future<bool> updateProjectStage(int projectId, Map<String, dynamic> data)`

---

### 3.3. UI Components & Widgets (Frontend)

#### 1. `StageBadge` (`frontend/lib/shared/widgets/stage_badge.dart`) [NEW]
* Widget hiển thị Badge của Stage với hiệu ứng hiện đại:
  - Background Gradient nhẹ theo màu của từng Stage.
  - Border viền sáng tinh tế, bo góc pill (`BorderRadius.circular(16)`).
  - Icon đặc trưng + Mã Stage (ví dụ: `[✦ S1: Problem Validation]`).
  - Tooltip khi hover: Hiển thị mục tiêu cốt lõi của Stage.

#### 2. `StageSelectorHeader` (`frontend/lib/modules/hologram_hub/widgets/stage_selector_header.dart`) [NEW]
* Tích hợp ở thanh tiêu đề của Hologram Hub:
  - Dropdown chọn Project hiện tại.
  - Hiển thị ngay bên cạnh là `StageBadge` của Project đó.
  - Nút biểu tượng "Tra cứu Chính sách Giai đoạn" (Policy Info Button) để mở `StagePolicyDialog`.

#### 3. `StagePolicyDialog` (`frontend/lib/modules/hologram_hub/widgets/stage_policy_dialog.dart`) [NEW]
* Dialog hiển thị thông tin chi tiết chính sách quản trị của Stage hiện tại:
  - **Mục tiêu tối thượng (Primary Goal)** & Các câu hỏi trọng tâm.
  - **Công cụ khuyến nghị dùng (Recommended Methods)** vs **Công cụ tạm tắt (Deemphasized)**.
  - **Chỉ số cần đo (Primary Metrics)** & **Agent ưu tiên (Priority Agents)**.

---

### 3.4. State Management Integration (`HologramHubController`)

#### Cập nhật [HologramHubController](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart):
* Khởi tạo `StageService`.
* Khai báo Observable State:
  - `final Rx<StageContextModel?> stageContext = Rx<StageContextModel?>(null);`
  - `final Rx<ProjectStage> currentProjectStage = ProjectStage.s1ProblemValidation.obs;`
  - `final RxBool isStageLoading = false.obs;`
* Hàm `loadStageContext(int? projectId)`:
  - Gọi `stageService.getStageContext(projectId: projectId)`.
  - Cập nhật `stageContext.value` và `currentProjectStage.value`.
* Tích hợp vào `onInit()` và sự kiện đổi Project trong Hologram Hub.

---

## 4. KẾ HOẠCH KIỂM THỬ PHASE 1 (VERIFICATION PLAN)

### 4.1. Automated Backend Tests
Tạo file: `backend/app/tests/founder_os/test_stage_foundation.py`
```bash
pytest backend/app/tests/founder_os/test_stage_foundation.py -v
```
- **Test 1:** Xác thực từ điển 7 Stage trong `ManagementPolicyEngine` đầy đủ, chính xác.
- **Test 2:** Xác thực `StageResolverService` khi truyền `project_id` cụ thể.
- **Test 3:** Xác thực `StageResolverService` fallback về Project P0 khi `project_id=None`.
- **Test 4:** Xác thực các endpoints API `/context`, `/policy/{stage}`, `/project/{project_id}`.

### 4.2. Automated Frontend Tests
Tạo file: `frontend/test/modules/stage_foundation_test.dart`
```bash
cd frontend && flutter test test/modules/stage_foundation_test.dart
```
- **Test 1:** Parse `StageContextModel` và `StagePolicyModel` từ JSON API.
- **Test 2:** Render Widget `StageBadge` hiển thị đúng màu gradient và nhãn cho cả 7 Stage (S0..S6).
- **Test 3:** Render `StageSelectorHeader` và kiểm tra sự kiện mở `StagePolicyDialog`.

---

## 5. CHECKLIST CÁC FILE SẼ TRIỂN KHAI TRONG PHASE 1

### Backend:
- [ ] `backend/app/founder_os/strategy/models.py` [MODIFY]
- [ ] `backend/app/platform/auth/models.py` [MODIFY]
- [ ] `backend/app/founder_os/strategy/schemas/stage_schemas.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/stage_resolver_service.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/management_policy_engine.py` [NEW]
- [ ] `backend/app/founder_os/strategy/routers/stage_foundation_router.py` [NEW]
- [ ] `backend/app/founder_os/strategy/router.py` [MODIFY]
- [ ] `backend/app/tests/founder_os/test_stage_foundation.py` [NEW]

### Frontend:
- [ ] `frontend/lib/data/models/stage_model.dart` [NEW]
- [ ] `frontend/lib/data/services/stage_service.dart` [NEW]
- [ ] `frontend/lib/shared/widgets/stage_badge.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_selector_header.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_policy_dialog.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` [MODIFY]
- [ ] `frontend/test/modules/stage_foundation_test.dart` [NEW]
