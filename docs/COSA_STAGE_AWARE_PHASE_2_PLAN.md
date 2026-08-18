# KẾ HOẠCH TRIỂN KHAI CHI TIẾT — PHASE 2: EVIDENCE CORE & DECISION LINEAGE
## Trục Xương Sống Kiểm Chứng Giả Định, Thang Bằng Chứng (E0–E6) & Bộ Nhớ Quyết Định Công Ty

**Mục tiêu của Phase 2:** Xây dựng trục xương sống kiểm chứng sống còn cho startup và doanh nghiệp từ S0 đến S6: Quản lý Giả định (`Hypothesis`), Bằng chứng (`Evidence`) theo Thang đo **Evidence Ladder (E0 → E6)**, Ma trận Rủi ro Giả định (Assumption Risk Matrix), và gắn vết nguồn gốc bằng chứng (`evidence_refs`) vào mọi Quyết định (`Decision`) làm nền tảng cho **Company Memory**.

---

## 1. TỔNG QUAN KIẾN TRÚC PHASE 2 (FULL-STACK)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FLUTTER FRONTEND (GETX)                         │
│  - EvidenceLadderBadge (E0 Opinion -> E6 Scalable Evidence)            │
│  - HypothesisCard & EvidenceItemCard (UI hiển thị chi tiết)            │
│  - AssumptionRiskMatrixWidget (Trực quan hóa Importance vs Uncertainty)│
│  - EvidenceBackboneDrawer & DecisionLogModal (Quản lý & Company Memory)│
│  - EvidenceService & HologramHubController State                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST API
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (CORE)                         │
│  - EvidenceRouter (/api/v1/strategy/evidence/...)                      │
│  - EvidenceEngineService (Evidence Ladder E0-E6 & Auto Status Engine)  │
│  - DecisionLogService (Company Memory & Decision Lineage)              │
│  - SQLAlchemy Models (Hypothesis, Evidence, StrategicDecision Update)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CHI TIẾT THIẾT KẾ KỸ THUẬT BACKEND

### 2.1. Database Models (`backend/app/founder_os/strategy/models.py`)

#### 1. Tạo model `Hypothesis` (Giả Định):
```python
class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    # Phân loại giả định
    category: Mapped[str] = mapped_column(String(50), index=True)  
    # customer | problem | solution | pricing | channel | revenue | cost | technology | legal | operational
    
    statement: Mapped[str] = mapped_column(Text)
    
    # Đo lường rủi ro & độ bất định
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 (ít quan trọng) - 1.0 (sống còn)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5) # 0.0 (đã biết chắc) - 1.0 (hoàn toàn mù mờ)
    risk_score: Mapped[float] = mapped_column(Float, default=0.25) # importance * uncertainty
    
    # Điểm bằng chứng & độ tin cậy
    evidence_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 - 1.0 (tính từ Evidence Ladder)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Trạng thái giả định
    status: Mapped[str] = mapped_column(String(50), default="UNTESTED", index=True)
    # UNTESTED | TESTING | SUPPORTED | CONTRADICTED | INVALIDATED
    
    stage_created: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION")
    
    # Liên kết bằng chứng & thực nghiệm
    evidence_refs: Mapped[dict] = mapped_column(JSONB, default=list) # List[int]: evidence_ids
    experiment_refs: Mapped[dict] = mapped_column(JSONB, default=list)
    
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2. Tạo model `Evidence` (Bằng Chứng Thực Tế):
```python
class Evidence(Base):
    __tablename__ = "evidences"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    # Loại bằng chứng
    type: Mapped[str] = mapped_column(String(50), index=True)
    # interview | observation | behavioral | transaction | usage | campaign | financial | legal | market_signal
    
    # Nấc thang bằng chứng (Evidence Ladder)
    ladder_level: Mapped[str] = mapped_column(String(50), default="E1_STATED_INTEREST", index=True)
    # E0_OPINION (0.0)
    # E1_STATED_INTEREST (0.2)
    # E2_OBSERVED_PROBLEM (0.4)
    # E3_BEHAVIORAL_COMMITMENT (0.7)
    # E4_ECONOMIC_COMMITMENT (0.9)
    # E5_REPEAT_BEHAVIOR (0.95)
    # E6_SCALABLE_EVIDENCE (1.0)
    
    source: Mapped[str] = mapped_column(String(255)) # Ví dụ: "Phỏng vấn KH 05 - Khách sạn Grand", "Stripe Invoice #102"
    claim_supported: Mapped[str] = mapped_column(Text) # Tóm tắt bằng chứng chứng minh điều gì
    
    strength: Mapped[str] = mapped_column(String(50), default="medium") # weak | medium | strong
    direction: Mapped[str] = mapped_column(String(50), default="supports") # supports | contradicts | neutral
    
    hypothesis_refs: Mapped[dict] = mapped_column(JSONB, default=list) # List[int]: hypothesis_ids
    artifact_refs: Mapped[dict] = mapped_column(JSONB, default=list)   # List[int]: vault_document_ids
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)     # Dữ liệu chi tiết, link recording, metrics
    
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 3. Cập nhật model `StrategicDecision` (Quyết Định Chiến Lược & Company Memory):
```python
# Mở rộng StrategicDecision để lưu vết bằng chứng
class StrategicDecision(Base):
    __tablename__ = "strategic_decisions"
    
    # ... Các cột id, workspace_id, brain_id giữ nguyên ...
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    selected_option: Mapped[str] = mapped_column(Text)
    alternatives_jsonb: Mapped[dict] = mapped_column(JSONB, default=list) # Các phương án thay thế đã bỏ qua
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Lý do ra quyết định
    
    evidence_refs: Mapped[dict] = mapped_column(JSONB, default=list)     # List[int]: Các evidence làm căn cứ
    stage: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION")
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="active") # active | superseded | reviewed | deprecated
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

### 2.2. Schemas & Enums (`backend/app/founder_os/strategy/schemas/evidence_schemas.py`) [NEW]
* **Enums:**
  - `HypothesisCategoryEnum`: `customer`, `problem`, `solution`, `pricing`, `channel`, `revenue`, `cost`, `technology`, `legal`, `operational`.
  - `HypothesisStatusEnum`: `UNTESTED`, `TESTING`, `SUPPORTED`, `CONTRADICTED`, `INVALIDATED`.
  - `EvidenceLadderLevelEnum`: `E0_OPINION`, `E1_STATED_INTEREST`, `E2_OBSERVED_PROBLEM`, `E3_BEHAVIORAL_COMMITMENT`, `E4_ECONOMIC_COMMITMENT`, `E5_REPEAT_BEHAVIOR`, `E6_SCALABLE_EVIDENCE`.
  - `EvidenceStrengthEnum`: `weak`, `medium`, `strong`.
  - `EvidenceDirectionEnum`: `supports`, `contradicts`, `neutral`.
* **Pydantic Schemas:**
  - `HypothesisCreate`, `HypothesisUpdate`, `HypothesisResponse`
  - `EvidenceCreate`, `EvidenceUpdate`, `EvidenceResponse`
  - `StrategicDecisionCreate`, `StrategicDecisionResponse`, `CompanyMemoryQueryRequest`, `CompanyMemoryQueryResponse`
  - `AssumptionMatrixResponse`: Trả về danh sách giả định phân nhóm theo 4 góc phần tư rủi ro.

---

### 2.3. Services Layer (Backend)

#### 1. `EvidenceEngineService` (`backend/app/founder_os/strategy/services/evidence_engine_service.py`) [NEW]
* **Trọng số chuẩn của Evidence Ladder:**
  ```python
  LADDER_WEIGHTS = {
      "E0_OPINION": 0.0,
      "E1_STATED_INTEREST": 0.2,
      "E2_OBSERVED_PROBLEM": 0.4,
      "E3_BEHAVIORAL_COMMITMENT": 0.7,
      "E4_ECONOMIC_COMMITMENT": 0.9,
      "E5_REPEAT_BEHAVIOR": 0.95,
      "E6_SCALABLE_EVIDENCE": 1.0,
  }
  STRENGTH_MULTIPLIERS = {"weak": 0.6, "medium": 1.0, "strong": 1.3}
  ```
* **Thuật toán tái tính điểm `evidence_score` của Giả định:**
  - Khi một `Evidence` được thêm/sửa/xóa:
    - Quét toàn bộ `evidences` gắn với `Hypothesis`.
    - Tính tổng điểm có trọng số:
      $$Score = \sum \left( \text{LadderWeight} \times \text{StrengthMultiplier} \times \text{DirectionSign} \right)$$
    - Chuẩn hóa về thang $[0.0, 1.0]$.
    - Cập nhật trạng thái `status`:
      - Nếu chưa có bằng chứng nào: `UNTESTED`.
      - Đang có bằng chứng E1–E2 hoặc điểm $< 0.7$: `TESTING`.
      - Điểm $\ge 0.75$ VÀ có ít nhất 1 bằng chứng $\ge$ E3 (Behavioral / Economic Commitment): `SUPPORTED` (Đã kiểm chứng thành công).
      - Điểm âm hoặc có bằng chứng thực nghiệm phủ định mạnh: `CONTRADICTED` / `INVALIDATED`.
* **Ma trận Rủi ro Giả định (Assumption Risk Matrix):**
  - Tính `risk_score = importance * uncertainty`.
  - Phân loại 4 nhóm:
    1. **Critical Test First (Rủi ro cao nhất):** `importance >= 0.7` và `uncertainty >= 0.6`.
    2. **Monitor (Cần theo dõi):** `importance < 0.7` và `uncertainty >= 0.6`.
    3. **Important Low Risk (Quan trọng nhưng đã rõ):** `importance >= 0.7` và `uncertainty < 0.6`.
    4. **Low Priority (Ít quan trọng):** `importance < 0.7` và `uncertainty < 0.6`.

#### 2. `DecisionLogService` (`backend/app/founder_os/strategy/services/decision_log_service.py`) [NEW]
* **Quản lý Bộ Nhớ Quyết Định Công Ty (Company Memory):**
  - Hàm `record_decision(...)`: Ghi lại câu hỏi, phương án chọn, các phương án loại trừ, lý do và danh sách `evidence_refs`.
  - Hàm `query_company_memory(query_text, project_id)`: Tìm kiếm lý do ra quyết định trong quá khứ dựa trên `question`, `rationale` và trích xuất bằng chứng minh chứng (`evidence_refs`).

---

### 2.4. API Router Layer (`backend/app/founder_os/strategy/routers/evidence_router.py`) [NEW]
* **Giả Định (Hypotheses):**
  - `GET /api/v1/strategy/evidence/hypotheses`: Lấy danh sách giả định (filter theo `project_id`, `category`, `status`).
  - `POST /api/v1/strategy/evidence/hypotheses`: Tạo giả định mới.
  - `PATCH /api/v1/strategy/evidence/hypotheses/{id}`: Cập nhật giả định.
  - `DELETE /api/v1/strategy/evidence/hypotheses/{id}`: Xóa giả định.
  - `GET /api/v1/strategy/evidence/matrix/{project_id}`: Lấy Ma trận Rủi ro Giả định 4 góc phần tư.
* **Bằng Chứng (Evidences):**
  - `GET /api/v1/strategy/evidence/evidences`: Lấy danh sách bằng chứng (filter theo `project_id`, `type`, `ladder_level`).
  - `POST /api/v1/strategy/evidence/evidences`: Thêm bằng chứng mới (tự động kích hoạt tính lại `evidence_score` của các Hypotheses liên quan).
  - `DELETE /api/v1/strategy/evidence/evidences/{id}`: Xóa bằng chứng.
* **Quyết Định & Company Memory:**
  - `GET /api/v1/strategy/evidence/decisions`: Lấy lịch sử quyết định.
  - `POST /api/v1/strategy/evidence/decisions`: Ghi nhận quyết định mới kèm `evidence_refs`.
  - `GET /api/v1/strategy/evidence/decisions/memory`: Tra cứu Company Memory kèm bằng chứng.

---

## 3. CHI TIẾT THIẾT KẾ KỸ THUẬT FRONTEND (FLUTTER)

### 3.1. Data Models (`frontend/lib/data/models/evidence_model.dart`) [NEW]
* `enum HypothesisCategory`: `customer`, `problem`, `solution`, `pricing`, `channel`, `revenue`, `cost`, `technology`, `legal`, `operational`.
* `enum HypothesisStatus`: `untested`, `testing`, `supported`, `contradicted`, `invalidated`.
* `enum EvidenceLadderLevel`:
  - `e0Opinion` ("E0: Ý kiến cá nhân", weight: 0.0, color: Slate)
  - `e1StatedInterest` ("E1: Khách hàng nói thích", weight: 0.2, color: Blue)
  - `e2ObservedProblem` ("E2: Nỗi đau thực tế quan sát được", weight: 0.4, color: Indigo)
  - `e3BehavioralCommitment` ("E3: Cam kết hành vi / Thời gian", weight: 0.7, color: Purple)
  - `e4EconomicCommitment` ("E4: Trả tiền thật / Đặt cọc Pilot", weight: 0.9, color: Emerald Green)
  - `e5RepeatBehavior` ("E5: Khách mua lại / Tái gia hạn", weight: 0.95, color: Teal)
  - `e6ScalableEvidence` ("E6: Dữ liệu chuyển đổi quy mô lớn", weight: 1.0, color: Amber)
* `HypothesisModel`, `EvidenceModel`, `StrategicDecisionModel`, `AssumptionMatrixModel`.

---

### 3.2. Data Service Layer (`frontend/lib/data/services/evidence_service.dart`) [NEW]
* Tương tác REST API:
  - `Future<List<HypothesisModel>> getHypotheses({int? projectId, String? category, String? status})`
  - `Future<HypothesisModel?> createHypothesis(Map<String, dynamic> data)`
  - `Future<List<EvidenceModel>> getEvidences({int? projectId, String? ladderLevel})`
  - `Future<EvidenceModel?> addEvidence(Map<String, dynamic> data)`
  - `Future<AssumptionMatrixModel?> getAssumptionMatrix(int projectId)`
  - `Future<List<StrategicDecisionModel>> getDecisions({int? projectId})`
  - `Future<StrategicDecisionModel?> recordDecision(Map<String, dynamic> data)`

---

### 3.3. UI Components & Widgets (Flutter)

#### 1. `EvidenceLadderBadge` (`frontend/lib/shared/widgets/evidence_ladder_badge.dart`) [NEW]
* Widget hiển thị nấc thang bằng chứng với màu gradient và trọng số:
  - Badge gọn: `[E4: Trả Tiền Pilot]` với viền sáng Emerald Green.
  - Tooltip hiển thị: Mức độ tin cậy và giải thích nấc thang.

#### 2. `HypothesisCard` (`frontend/lib/modules/hologram_hub/widgets/evidence/hypothesis_card.dart`) [NEW]
* Thẻ hiển thị Giả định:
  - Header: Category Tag (Khách hàng, Giá bán, Giải pháp...) + Status Badge (`TESTING`, `SUPPORTED`...).
  - Statement: Câu phát biểu giả định rõ ràng.
  - Risk Score Meter: Thanh đo mức độ rủi ro (Đỏ: Rất cao, Vàng: Trung bình, Xanh: Thấp).
  - Evidence Score Gauge: Vòng tròn đo % bằng chứng thu thập được.
  - Footer: Nút "Thêm Bằng Chứng Mới" & "Xem Bằng Chứng Liên Quan".

#### 3. `EvidenceItemCard` (`frontend/lib/modules/hologram_hub/widgets/evidence/evidence_item_card.dart`) [NEW]
* Thẻ hiển thị Bằng chứng:
  - Nấc thang `EvidenceLadderBadge` (E0..E6).
  - Hướng tác động: `Ủng hộ (+)` màu xanh hoặc `Phủ định (-)` màu đỏ.
  - Tóm tắt bằng chứng & Nguồn trích dẫn (`source`).

#### 4. `AssumptionRiskMatrixWidget` (`frontend/lib/modules/hologram_hub/widgets/evidence/assumption_risk_matrix_widget.dart`) [NEW]
* Biểu đồ trực quan hóa Ma trận Rủi ro (Importance vs Uncertainty) chia 4 góc phần tư:
  - **Góc trên-phải (Vùng Đỏ - Critical Test First):** Danh sách các giả định cần lập tức thiết kế thực nghiệm kiểm chứng.
  - **Góc trên-trái (Vùng Vàng - Monitor):** Cần theo dõi thêm.
  - **Góc dưới-phải (Vùng Xanh - Important Low Risk):** Đã kiểm chứng rõ ràng.

#### 5. `EvidenceBackboneDrawer` (`frontend/lib/modules/hologram_hub/widgets/evidence/evidence_backbone_drawer.dart`) [NEW]
* Drawer mở ra từ cạnh phải của Hologram Hub:
  - Tab 1: Danh sách Giả định (`Hypotheses Backlog`) + Bộ lọc Category & Status.
  - Tab 2: Ma trận Rủi ro Giả định (`Risk Matrix 2x2`).
  - Tab 3: Thư viện Bằng chứng (`Evidence Vault`) theo Ladder E0–E6.

#### 6. `DecisionLogModal` (`frontend/lib/modules/hologram_hub/widgets/evidence/decision_log_modal.dart`) [NEW]
* Modal tra cứu Bộ nhớ Quyết định Công ty (Company Memory):
  - Danh sách quyết định chiến lược theo thời gian.
  - Hiển thị rõ: *Câu hỏi -> Phương án chọn -> Phương án loại bỏ -> Lý do -> Bằng chứng minh chứng (`evidence_refs`)*.

---

### 3.4. State Management Integration (`HologramHubController`)

#### Cập nhật `HologramHubController`:
* Khởi tạo `EvidenceService`.
* Khai báo Observable State:
  - `final hypothesesList = <HypothesisModel>[].obs;`
  - `final evidencesList = <EvidenceModel>[].obs;`
  - `final criticalHypotheses = <HypothesisModel>[].obs;` // Top giả định rủi ro cao nhất cần test
  - `final decisionsList = <StrategicDecisionModel>[].obs;`
  - `final isEvidenceLoading = false.obs;`
* Hàm `loadEvidenceBackbone(int? projectId)`:
  - Tự động nạp danh sách Giả định & Bằng chứng khi đổi Project.
  - Lọc ra `criticalHypotheses` để làm đầu vào cho Phase 3 (Next Best Action).

---

## 4. KẾ HOẠCH KIỂM THỬ PHASE 2 (VERIFICATION PLAN)

### 4.1. Automated Backend Tests
Tạo file: `backend/app/tests/test_evidence_engine.py`
- **Test 1 (Evidence Ladder Scoring):**
  - Thêm 1 bằng chứng E1 (Ý kiến) → `evidence_score = 0.2`, status = `TESTING`.
  - Thêm tiếp 1 bằng chứng E4 (Trả tiền thật) → `evidence_score >= 0.75`, status tự động chuyển sang `SUPPORTED`.
- **Test 2 (Contradiction / Invalidation):**
  - Thêm bằng chứng E4 với direction `contradicts` → status tự động chuyển sang `CONTRADICTED`.
- **Test 3 (Assumption Risk Matrix):**
  - Xác thực phân nhóm 4 góc phần tư rủi ro (Critical Test First, Monitor, Low Risk).
- **Test 4 (Decision Lineage & Company Memory):**
  - Ghi nhận quyết định kèm `evidence_refs` và truy vấn lại đúng bằng chứng minh chứng.

### 4.2. Automated Frontend Tests
Tạo file: `frontend/test/stage_evidence_test.dart`
- **Test 1:** Parse `HypothesisModel`, `EvidenceModel` từ JSON API.
- **Test 2:** Render `EvidenceLadderBadge` cho đủ 7 nấc thang (E0..E6) với đúng màu sắc.
- **Test 3:** Render `HypothesisCard` và hiển thị đúng điểm Evidence Score %.

---

## 5. CHECKLIST CÁC FILE SẼ TRIỂN KHAI TRONG PHASE 2

### Backend:
- [ ] `backend/app/founder_os/strategy/models.py` [MODIFY] (Thêm `Hypothesis`, `Evidence`, cập nhật `StrategicDecision`)
- [ ] `backend/app/founder_os/strategy/schemas/evidence_schemas.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/evidence_engine_service.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/decision_log_service.py` [NEW]
- [ ] `backend/app/founder_os/strategy/routers/evidence_router.py` [NEW]
- [ ] `backend/app/founder_os/strategy/router.py` [MODIFY]
- [ ] `backend/app/tests/test_evidence_engine.py` [NEW]

### Frontend:
- [ ] `frontend/lib/data/models/evidence_model.dart` [NEW]
- [ ] `frontend/lib/data/services/evidence_service.dart` [NEW]
- [ ] `frontend/lib/shared/widgets/evidence_ladder_badge.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/evidence/hypothesis_card.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/evidence/evidence_item_card.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/evidence/assumption_risk_matrix_widget.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/evidence/evidence_backbone_drawer.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/evidence/decision_log_modal.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` [MODIFY]
- [ ] `frontend/test/stage_evidence_test.dart` [NEW]
