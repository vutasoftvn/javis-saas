# KẾ HOẠCH TRIỂN KHAI CHI TIẾT — PHASE 3: STAGE-AWARE WORKFLOWS & STRATEGY LENSES
## Khung Chiến Lược 4 Lăng Kính (PESTEL, SWOT, TOWS, BSC) & Kế Hoạch 12 Tuần (12WY) Đúng Giai Đoạn

**Mục tiêu của Phase 3:** Hiện thực hóa cơ chế quản trị chiến lược đa lăng kính (PESTEL, SWOT, TOWS, BSC) được may đo chính xác theo từng giai đoạn (S0–S6), kết nối trực tiếp với Trục Giả định & Bằng chứng (`Hypothesis` & `Evidence` từ Phase 2), và chuyển hóa thành các Kế hoạch thực thi 12 tuần (12-Week Year Tactics & Lead Indicators).

---

## 1. TỔNG QUAN VAI TRÒ CỦA 4 LĂNG KÍNH CHIẾN LƯỢC THEO STAGE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       S0: EXPLORE & OPPORTUNITY                             │
│  ► PESTEL (External Radar Lens) -> Quét 6 chiều vĩ mô -> Sinh Giả Định S0   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     S1: PROBLEM & S2: SOLUTION VALIDATION                   │
│  ► Evidence-backed SWOT: Điểm Mạnh/Yếu BẮT BUỘC có evidence_refs            │
│  ► TOWS Generator: Ghép SO, WO, ST, WT -> Sinh Critical Hypotheses          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     S3: BUSINESS & S4: GO-TO-MARKET                         │
│  ► TOWS Options -> Chuyển hóa thành Kế hoạch Hành Động 12 Tuần (12WY)       │
│  ► Phân bổ Lead Indicators (Chỉ số dẫn dắt) & Lag Indicators (Doanh thu)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     S5: OPERATE & GROW & S6: SCALE & GOVERN                 │
│  ► Mở Khóa BALANCED SCORECARD (BSC) 4 Trụ Cột:                              │
│    1. Financial (Tài chính: ARR, Runway, Gross Margin)                      │
│    2. Customer (Khách hàng: Retention, NPS, CAC Payback)                    │
│    3. Internal Operations (Vận hành: SLA, Velocity, Cycle Time)             │
│    4. Learning & Growth (Năng lực: AI Workforce, Team Capability)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CHI TIẾT THIẾT KẾ KỸ THUẬT BACKEND (FASTAPI)

### 2.1. Database Models (`backend/app/founder_os/strategy/models.py`)

#### 1. Mở rộng / Tạo mới `PestelSignal` (Tín hiệu Vĩ mô PESTEL):
```python
class PestelSignal(Base):
    __tablename__ = "pestel_signals"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    dimension: Mapped[str] = mapped_column(String(50), index=True) 
    # political | economic | social | technological | environmental | legal
    
    signal_title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    impact_level: Mapped[str] = mapped_column(String(50), default="medium") # high | medium | low
    time_horizon: Mapped[str] = mapped_column(String(50), default="medium_term") # short_term | medium_term | long_term
    
    # Liên kết chuyển hóa thành Giả định (Hypothesis) hoặc SWOT Opportunity/Threat
    resulting_hypothesis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hypotheses.id"), nullable=True)
    stage_captured: Mapped[str] = mapped_column(String(50), default="S0_EXPLORE")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 2. Mở rộng `SwotItem` với Bằng chứng bắt buộc (`evidence_refs`):
```python
class SwotItem(Base):
    __tablename__ = "swot_items"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    type: Mapped[str] = mapped_column(String(50), index=True) # STRENGTH | WEAKNESS | OPPORTUNITY | THREAT
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    
    # Quy tắc nghiêm ngặt: S & W bắt buộc có bằng chứng minh chứng
    evidence_refs: Mapped[dict] = mapped_column(JSONB, default=list) # List[int]: evidence_ids
    pestel_signal_ref: Mapped[Optional[int]] = mapped_column(ForeignKey("pestel_signals.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 3. Mở rộng `TowsOption` (Chiến lược Ghép Cặp TOWS):
```python
class TowsOption(Base):
    __tablename__ = "tows_options"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    tows_type: Mapped[str] = mapped_column(String(50), index=True) # SO | WO | ST | WT
    strategy_name: Mapped[str] = mapped_column(String(255))
    strategy_description: Mapped[str] = mapped_column(Text)
    
    linked_strength_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    linked_weakness_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    linked_opportunity_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    linked_threat_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # Chuyển hóa thành Giả định hoặc Tactic thực thi
    resulting_hypothesis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hypotheses.id"), nullable=True)
    tactics_12wy: Mapped[dict] = mapped_column(JSONB, default=list)
    
    status: Mapped[str] = mapped_column(String(50), default="proposed") # proposed | selected | archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 4. Model `BscScorecard` & `BscGoal` (Balanced Scorecard S5–S6):
```python
class BscGoal(Base):
    __tablename__ = "bsc_goals"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    perspective: Mapped[str] = mapped_column(String(50), index=True)
    # FINANCIAL | CUSTOMER | INTERNAL_OPERATIONS | LEARNING_GROWTH
    
    objective: Mapped[str] = mapped_column(String(255))
    kpi_name: Mapped[str] = mapped_column(String(255))
    target_value: Mapped[str] = mapped_column(String(100))
    current_value: Mapped[str] = mapped_column(String(100), default="0")
    
    initiatives: Mapped[dict] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(50), default="on_track") # on_track | at_risk | behind
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

### 2.2. Schemas & Enums (`backend/app/founder_os/strategy/schemas/lens_schemas.py`) [NEW]
* **Enums:**
  - `PestelDimensionEnum`: `political`, `economic`, `social`, `technological`, `environmental`, `legal`.
  - `SwotTypeEnum`: `STRENGTH`, `WEAKNESS`, `OPPORTUNITY`, `THREAT`.
  - `TowsTypeEnum`: `SO`, `WO`, `ST`, `WT`.
  - `BscPerspectiveEnum`: `FINANCIAL`, `CUSTOMER`, `INTERNAL_OPERATIONS`, `LEARNING_GROWTH`.
* **Pydantic Models:**
  - `PestelSignalCreate`, `PestelSignalResponse`
  - `SwotItemCreate`, `SwotItemResponse`
  - `TowsOptionCreate`, `TowsOptionResponse`, `TowsToTacticConvertRequest`
  - `BscGoalCreate`, `BscGoalResponse`
  - `StageLensSummaryResponse`: Trả về toàn bộ dữ liệu 4 lăng kính đã được lọc và phân quyền hiển thị theo Stage Policy.

---

### 2.3. Services Layer (`backend/app/founder_os/strategy/services/strategy_lens_service.py`) [NEW]
* **`StrategyLensService`** cung cấp:
  1. **PESTEL Engine:** Ghi nhận tín hiệu thị trường vĩ mô và hỗ trợ 1-click chuyển đổi tín hiệu thành Giả định (`create_hypothesis_from_signal`).
  2. **SWOT Evidence Validator:**
     - Khi thêm `STRENGTH` hoặc `WEAKNESS`: Kiểm tra và bắt buộc phải có ít nhất 1 `evidence_ref` hợp lệ.
     - Khi thêm `OPPORTUNITY` hoặc `THREAT`: Tự động gắn liên kết với `PestelSignal` nếu có.
  3. **TOWS Matrix Generator:**
     - Ghép cặp tự động giữa S/W và O/T sinh ra 4 nhóm chiến lược SO, WO, ST, WT.
     - Hàm `convert_tows_to_12wy_tactics(...)`: Tự động sinh `Hypothesis` và kế hoạch hành động 12 tuần.
  4. **BSC Gatekeeper (Khóa/Mở Khóa theo Stage):**
     - Kiểm tra `project.project_stage`: Nếu Stage < `S5_OPERATE_GROWTH`, trả về cảnh báo `StagePolicyException: Balanced Scorecard chỉ được kích hoạt từ S5 (Operate & Grow) để tránh lãng phí nguồn lực`.

---

### 2.4. API Router (`backend/app/founder_os/strategy/routers/strategy_lens_router.py`) [NEW]
* `GET /api/v1/strategy/lenses/summary/{project_id}`: Lấy tổng hợp 4 lăng kính theo đúng Stage.
* `GET/POST /api/v1/strategy/lenses/pestel`: CRUD tín hiệu PESTEL.
* `POST /api/v1/strategy/lenses/pestel/{signal_id}/to-hypothesis`: Chuyển tín hiệu PESTEL thành Giả định.
* `GET/POST /api/v1/strategy/lenses/swot`: CRUD SWOT item (có kiểm tra `evidence_refs`).
* `GET/POST /api/v1/strategy/lenses/tows`: CRUD ma trận TOWS.
* `POST /api/v1/strategy/lenses/tows/{option_id}/generate-tactics`: Sinh chiến thuật 12 tuần từ TOWS.
* `GET/POST /api/v1/strategy/lenses/bsc`: Quản lý mục tiêu BSC (Chỉ cho phép tại S5–S6).

---

## 3. CHI TIẾT THIẾT KẾ KỸ THUẬT FRONTEND (FLUTTER)

### 3.1. Data Models & Services (`frontend/lib/data/models/strategy_lens_model.dart` & `strategy_lens_service.dart`)
* `PestelSignalModel`, `SwotItemModel`, `TowsOptionModel`, `BscGoalModel`, `StageLensSummaryModel`.
* `StrategyLensService`: Gọi API tương ứng với backend.

---

### 3.2. UI Components & Dialogs (Flutter)

#### 1. `StrategyLensesHubModal` (`frontend/lib/modules/hologram_hub/widgets/lenses/strategy_lenses_hub_modal.dart`) [NEW]
* Modal trung tâm quản lý 4 Lăng kính Chiến lược:
  - Header: Hiển thị Stage hiện tại của Project và trạng thái các lăng kính (Khuyến nghị, Tùy chọn, Khóa).
  - Tab 1: **PESTEL Radar** (Tín hiệu vĩ mô).
  - Tab 2: **SWOT có Bằng Chứng** (Hiển thị badge E0–E6 cho từng điểm Mạnh/Yếu).
  - Tab 3: **Ma Trận TOWS** (SO, WO, ST, WT & Nút sinh Kế hoạch 12 Tuần).
  - Tab 4: **Balanced Scorecard (BSC)** (4 trụ cột, nếu < S5 sẽ hiển thị màn hình khóa thông minh giải thích lý do).

#### 2. `PestelRadarWidget` (`frontend/lib/modules/hologram_hub/widgets/lenses/pestel_radar_widget.dart`) [NEW]
* Giao diện lưới 6 chiều vĩ mô (Chính trị, Kinh tế, Xã hội, Công nghệ, Môi trường, Pháp lý) với nút bấm "+ Tín hiệu" và "Sinh Giả Định".

#### 3. `SwotEvidenceGridWidget` (`frontend/lib/modules/hologram_hub/widgets/lenses/swot_evidence_grid_widget.dart`) [NEW]
* Ma trận 4 ô SWOT:
  - Ô S & W: Hiển thị danh sách bằng chứng minh chứng kèm `EvidenceLadderBadge`.
  - Ô O & T: Hiển thị nguồn tín hiệu từ PESTEL.

#### 4. `TowsMatrixWidget` (`frontend/lib/modules/hologram_hub/widgets/lenses/tows_matrix_widget.dart`) [NEW]
* Ma trận giao thoa TOWS (SO: Đột phá, WO: Khắc phục, ST: Phòng thủ, WT: Sinh tồn) với nút "Tạo Chiến Thuật 12 Tuần".

#### 5. `BscScorecardWidget` (`frontend/lib/modules/hologram_hub/widgets/lenses/bsc_scorecard_widget.dart`) [NEW]
* 4 Trụ cột Quản trị: Tài chính, Khách hàng, Vận hành, Năng lực & Con người kèm thanh tiến độ KPI.

---

### 3.3. Tích Hợp Controller & View
* Cập nhật `HologramHubController`:
  - Observables `lensSummary`, `pestelSignals`, `swotItems`, `towsOptions`, `bscGoals`.
  - Hàm `loadStageLensesData(projectId)`, `createPestelSignal()`, `createSwotItem()`, `generateTowsTactics()`.
* Cập nhật `StageSelectorHeader`: Thêm nút truy cập nhanh **"Lăng Kính Chiến Lược (Lenses)"**.

---

## 4. KẾ HOẠCH KIỂM THỬ (VERIFICATION PLAN)

### 4.1. Automated Backend Tests (`backend/app/tests/test_strategy_lenses.py`)
- `test_pestel_signal_to_hypothesis_conversion()`: Tạo tín hiệu PESTEL và chuyển thành Giả định S0/S1.
- `test_swot_requires_evidence_for_strength_weakness()`: Xác thực bắt buộc `evidence_refs` cho S/W.
- `test_tows_option_generates_12wy_tactics()`: Sinh chiến thuật 12 tuần từ cặp TOWS SO/WO.
- `test_bsc_stage_gating_policy()`: Chặn tạo BSC ở S1–S3 và cho phép mở ở S5–S6.

### 4.2. Automated Frontend Tests (`frontend/test/stage_lenses_test.dart`)
- Kiểm tra deserialize models PESTEL, SWOT, TOWS, BSC.
- Kiểm tra render `SwotEvidenceGridWidget` hiển thị `EvidenceLadderBadge`.
- Kiểm tra render `BscScorecardWidget` hiển thị trạng thái khóa ở S1–S3 và mở ở S5–S6.

---

## 5. CHECKLIST CÁC FILE SẼ TRIỂN KHAI TRONG PHASE 3

### Backend:
- [ ] `backend/app/founder_os/strategy/models.py` [MODIFY] (Tạo `PestelSignal`, `BscGoal`, cập nhật `SwotItem`, `TowsOption`)
- [ ] `backend/app/founder_os/strategy/schemas/lens_schemas.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/strategy_lens_service.py` [NEW]
- [ ] `backend/app/founder_os/strategy/routers/strategy_lens_router.py` [NEW]
- [ ] `backend/app/founder_os/strategy/router.py` [MODIFY]
- [ ] `backend/app/tests/test_strategy_lenses.py` [NEW]

### Frontend:
- [ ] `frontend/lib/data/models/strategy_lens_model.dart` [NEW]
- [ ] `frontend/lib/data/services/strategy_lens_service.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/lenses/strategy_lenses_hub_modal.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/lenses/pestel_radar_widget.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/lenses/swot_evidence_grid_widget.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/lenses/tows_matrix_widget.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/lenses/bsc_scorecard_widget.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_selector_header.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` [MODIFY]
- [ ] `frontend/test/stage_lenses_test.dart` [NEW]
