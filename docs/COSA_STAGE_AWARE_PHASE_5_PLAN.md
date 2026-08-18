# KẾ HOẠCH TRIỂN KHAI CHI TIẾT — PHASE 5: 12-WEEK YEAR STRATEGIC EXECUTION LOOP & LEAD INDICATORS
## Vòng Lặp Thực Thi Chiến Lược 12 Tuần & Đo Lường Vận Tốc Chỉ Số Dẫn Dắt

**Mục tiêu của Phase 5:** Xây dựng cỗ máy thực thi chiến lược theo phương pháp luận **12-Week Year (12WY)** thích ứng với từng Stage của startup. Biến các chiến lược TOWS và Giả định cốt lõi thành các **Tactics hàng tuần** và đo lường trực tiếp thông qua **Lead Indicators (Chỉ số Dẫn dắt)** với điểm số kỷ luật thực thi hàng tuần (**Weekly Execution Score $\ge 85\%$**).

---

## 1. PHƯƠNG PHÁP LUẬN 12WY THÍCH ỨNG THEO STAGE (STAGE-AWARE 12WY)

| Giai Đoạn (Stage) | Độ dài chu kỳ thực tế | Bản chất Lead Indicators hàng tuần | Mục tiêu Kỷ luật Thực thi |
| :--- | :--- | :--- | :--- |
| **S0 - S2 (Validation)** | 2 - 4 tuần (Micro 12WY) | Số cuộc phỏng vấn khách hàng, số giả định kiểm chứng, số bản thử nghiệm prototype | Execution Score $\ge 85\%$, Vòng lặp phản hồi $\le 7$ ngày |
| **S3 - S4 (Business & GTM)**| 6 - 12 tuần | Số lead outbound, tỷ lệ demo chuyển đổi, số lần tối ưu kênh acquisition | Execution Score $\ge 85\%$, CAC/LTV kiểm chứng |
| **S5 - S6 (Scale & Govern)**| 12 tuần chuẩn | Tốc độ release sprint, SLA vận hành hệ thống, tỷ lệ giữ chân khách hàng (Retention) | Execution Score $\ge 90\%$, Bám sát BSC |

---

## 2. THIẾT KẾ KỸ THUẬT BACKEND (FASTAPI + SQLALCHEMY)

### 2.1. Database Models (`backend/app/founder_os/strategy/models.py`)

#### 1. Model `TwelveWeekCycle` (Chu kỳ thực thi 12 tuần):
```python
class TwelveWeekCycle(Base):
    __tablename__ = "twelve_week_cycles"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    title: Mapped[str] = mapped_column(String(255)) # Ví dụ: "Q1 12WY: Đạt Product-Market Fit cho AI Co-founder"
    vision_statement: Mapped[str] = mapped_column(Text, default="")
    stage_at_start: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION")
    
    current_week: Mapped[int] = mapped_column(Integer, default=1) # 1 -> 12
    total_weeks: Mapped[int] = mapped_column(Integer, default=12)
    
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE") # ACTIVE | COMPLETED | PAUSED
    overall_execution_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 -> 100.0%
    
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 2. Model `TacticalExecutionItem` (Hành động chiến thuật tuần & Chỉ số dẫn dắt):
```python
class TacticalExecutionItem(Base):
    __tablename__ = "tactical_execution_items"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True)
    
    week_number: Mapped[int] = mapped_column(Integer, index=True) # 1 -> 12
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    
    # Liên kết với TOWS hoặc Hypothesis nguồn
    tows_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tows_options.id"), nullable=True)
    hypothesis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hypotheses.id"), nullable=True)
    
    # Chỉ số dẫn dắt (Lead Indicator)
    lead_indicator_name: Mapped[str] = mapped_column(String(255)) # E.g., "Số buổi phỏng vấn KH"
    target_count: Mapped[int] = mapped_column(Integer, default=1)
    actual_count: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(50), default="PLANNED") # PLANNED | IN_PROGRESS | DONE | BLOCKED
    owner_role: Mapped[str] = mapped_column(String(100), default="Founder")
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 3. Model `WeeklyAccountabilityReview` (Nhật ký họp kiểm điểm WAM):
```python
class WeeklyAccountabilityReview(Base):
    __tablename__ = "weekly_accountability_reviews"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True)
    
    week_number: Mapped[int] = mapped_column(Integer)
    execution_score: Mapped[float] = mapped_column(Float, default=0.0) # % hoàn thành
    
    total_planned: Mapped[int] = mapped_column(Integer, default=0)
    total_completed: Mapped[int] = mapped_column(Integer, default=0)
    
    key_breakthroughs: Mapped[dict] = mapped_column(JSONB, default=list) # List[str]
    root_cause_blocks: Mapped[dict] = mapped_column(JSONB, default=list) # List[str]
    ai_recommendations: Mapped[dict] = mapped_column(JSONB, default=list) # List[str]
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

### 2.2. Schemas (`backend/app/founder_os/strategy/schemas/twelve_wy_schemas.py`) [NEW]
* `TwelveWeekCycleCreate`, `TwelveWeekCycleResponse`.
* `TacticalItemCreate`, `TacticalItemUpdate`, `TacticalItemResponse`.
* `WeeklyReviewResponse`, `CycleDashboardResponse`.

---

### 2.3. Services (`backend/app/founder_os/strategy/services/twelve_wy_service.py`) [NEW]
* **`TwelveWyService`** cung cấp:
  1. `get_or_create_active_cycle(db, workspace_id, project_id)`: Tự động khởi tạo chu kỳ 12 tuần nếu chưa có.
  2. `create_tactic(db, workspace_id, payload)`: Tạo tactic mới kèm chỉ số dẫn dắt.
  3. `update_tactic_progress(db, workspace_id, tactic_id, actual_count, status)`: Cập nhật tiến độ lead indicator và tính toán lại điểm số tuần.
  4. `generate_weekly_review(db, workspace_id, cycle_id, week_number)`: Tổng kết buổi họp WAM tự động bằng AI.
  5. `get_cycle_dashboard(db, workspace_id, project_id)`: Trả về toàn cảnh 12 tuần, điểm số từng tuần, danh sách tactics theo tuần.

---

### 2.4. Router (`backend/app/founder_os/strategy/routers/twelve_wy_router.py`) [NEW]
* `GET /api/v1/strategy/12wy/dashboard/{project_id}`
* `POST /api/v1/strategy/12wy/cycle`
* `POST /api/v1/strategy/12wy/tactics`
* `PUT /api/v1/strategy/12wy/tactics/{tactic_id}`
* `POST /api/v1/strategy/12wy/weekly-review/{cycle_id}/{week_number}`

---

## 3. THIẾT KẾ KỸ THUẬT FRONTEND (FLUTTER)

### 3.1. Data Models & Service
* `TwelveWeekCycleModel`, `TacticalItemModel`, `WeeklyReviewModel`, `TwelveWyDashboardModel` trong [twelve_wy_model.dart](file:///Volumes/SSD/javis-saas/frontend/lib/data/models/twelve_wy_model.dart).
* `TwelveWyService` trong [twelve_wy_service.dart](file:///Volumes/SSD/javis-saas/frontend/lib/data/services/twelve_wy_service.dart).

---

### 3.2. UI Components (Flutter)
1. **`TwelveWeekTimelineBar`**: Thanh trượt 12 tuần ngang (Week 1 .. Week 12) hiển thị điểm số hoàn thành từng tuần và chỉ báo tuần hiện tại.
2. **`TacticalItemCard`**: Card hiển thị hành động chiến thuật, chỉ số dẫn dắt (Target vs Actual), nút tăng giảm actual count, nút check hoàn thành.
3. **`WeeklyExecutionGauge`**: Đồng hồ đo điểm kỷ luật thực thi tuần này (% với mốc chuẩn $\ge 85\%$).
4. **`TwelveWyHubModal`**: Modal quản trị toàn diện vòng lặp thực thi 12 tuần.
5. **Nút "12WY Loop"**: Tích hợp trực tiếp vào `StageSelectorHeader`.

---

## 4. KẾ HOẠCH KIỂM THỬ (VERIFICATION PLAN)

### 4.1. Automated Backend Tests (`backend/app/tests/test_twelve_wy_engine.py`)
- `test_get_or_create_active_cycle()`: Tự tạo chu kỳ 12 tuần đầu tiên.
- `test_create_tactic_and_progress_tracking()`: Thêm tactic, tăng chỉ số dẫn dắt và đánh dấu hoàn thành.
- `test_weekly_execution_score_calculation()`: Kiểm tra công thức tính điểm thực thi tuần ($\ge 85\%$).
- `test_generate_weekly_accountability_review()`: Tổng kết phiên họp WAM.

### 4.2. Automated Frontend Tests (`frontend/test/twelve_wy_test.dart`)
- Kiểm thử JSON deserialization của models 12WY.
- Kiểm thử Widget rendering: `WeeklyExecutionGauge`, `TacticalItemCard`, `TwelveWyHubModal`.

---

## 5. CHECKLIST CÁC FILE SẼ TRIỂN KHAI

### Backend:
- [ ] `backend/app/founder_os/strategy/models.py` [MODIFY] (Thêm `TwelveWeekCycle`, `TacticalExecutionItem`, `WeeklyAccountabilityReview`)
- [ ] `backend/app/founder_os/strategy/schemas/twelve_wy_schemas.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/twelve_wy_service.py` [NEW]
- [ ] `backend/app/founder_os/strategy/routers/twelve_wy_router.py` [NEW]
- [ ] `backend/app/founder_os/strategy/router.py` [MODIFY]
- [ ] `backend/app/tests/test_twelve_wy_engine.py` [NEW]

### Frontend:
- [ ] `frontend/lib/data/models/twelve_wy_model.dart` [NEW]
- [ ] `frontend/lib/data/services/twelve_wy_service.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/twelve_wy/weekly_execution_gauge.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/twelve_wy/tactical_item_card.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/twelve_wy/twelve_week_timeline_bar.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/twelve_wy/twelve_wy_hub_modal.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_selector_header.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` [MODIFY]
- [ ] `frontend/test/twelve_wy_test.dart` [NEW]
