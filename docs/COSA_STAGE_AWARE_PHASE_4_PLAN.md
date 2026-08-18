# KẾ HOẠCH TRIỂN KHAI CHI TIẾT — PHASE 4: STAGE GATE AUDITING & ANTI-PREMATURE SCALING GUARDRAILS
## Động Cơ Kiểm Định Chuyển Giai Đoạn & Hàng Rào Phòng Vệ Chống Mở Rộng Sớm

**Mục tiêu của Phase 4:** Xây dựng hệ thống thẩm định chuyển giai đoạn nghiêm ngặt ($S_k \to S_{k+1}$), đo lường chỉ số sẵn sàng chuyển stage (`readiness_score`), và thiết lập hàng rào cảnh báo sớm chống mở rộng quy mô non trẻ (Anti-Premature Scaling Guardrails) để ngăn ngừa 74% nguyên nhân thất bại của startup.

---

## 1. TIÊU CHUẨN KIỂM ĐỊNH STAGE GATE (TRANSITION CRITERIA MATRIX)

| Chuyển Giai Đoạn | Điều Kiện Tiên Quyết (Evidence & Metric Gates) | Mức Bằng Chứng Tối Thiểu | Rủi Ro Premature Cần Chặn |
| :--- | :--- | :--- | :--- |
| **$S_0 \to S_1$** (Explore $\to$ Problem) | Có ít nhất 3 tín hiệu PESTEL vĩ mô & 1 giả định phân khúc khách hàng rõ ràng | E1 (Stated Interest) | Không code sản phẩm khi chưa rõ đối tượng |
| **$S_1 \to S_2$** (Problem $\to$ Solution) | Giả định nỗi đau (Problem Hypothesis) đạt `evidence_score` $\ge 0.6$ từ $\ge 10$ phỏng vấn sâu | E2 (Observed Problem) / E3 (Behavioral) | Cấm chi tiền quảng cáo lớn ($> \$500$) |
| **$S_2 \to S_3$** (Solution $\to$ Business) | MVP giải quyết được nỗi đau, có ít nhất 3 cam kết trả tiền trước (Pre-order/LOI) | E3 (Behavioral) / E4 (Economic) | Cấm tuyển đội ngũ Sales full-time |
| **$S_3 \to S_4$** (Business $\to$ GTM) | Có ít nhất 10 giao dịch thực tế ($E_4$), Unit economics bước đầu khả thi ($CAC < LTV$) | E4 (Economic Commitment) | Cấm scale marketing đa kênh khi chưa có 1 kênh chuẩn |
| **$S_4 \to S_5$** (GTM $\to$ Operate) | Tỷ lệ giữ chân khách hàng tự nhiên $\ge 40\%$, có hành vi mua lại / gia hạn ($E_5$) | E5 (Repeat Behavior) | Cấm xây dựng kiến trúc enterprise phức tạp |
| **$S_5 \to S_6$** (Operate $\to$ Scale) | Unit economics dương ở quy mô lớn ($E_6$), Dòng tiền hoạt động dương hoặc ARR ổn định | E6 (Scalable Evidence) | Cấm M&A/mở rộng thị trường quốc tế khi chưa vững core |

---

## 2. CHI TIẾT THIẾT KẾ KỸ THUẬT BACKEND (FASTAPI)

### 2.1. Database Models (`backend/app/founder_os/strategy/models.py`)

#### 1. Model `StageTransitionAudit` (Nhật Ký Thẩm Định Stage Gate):
```python
class StageTransitionAudit(Base):
    __tablename__ = "stage_transition_audits"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    from_stage: Mapped[str] = mapped_column(String(50))
    to_stage: Mapped[str] = mapped_column(String(50))
    
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 -> 1.0 (>= 0.70 là Passed)
    audit_status: Mapped[str] = mapped_column(String(50)) # APPROVED | CONDITIONALLY_APPROVED | REJECTED
    
    passed_criteria: Mapped[dict] = mapped_column(JSONB, default=list) # List[Dict]
    missing_criteria: Mapped[dict] = mapped_column(JSONB, default=list) # List[Dict]
    detected_risks: Mapped[dict] = mapped_column(JSONB, default=list) # List[Dict]
    
    audited_by_agent: Mapped[str] = mapped_column(String(100), default="Stage Gate Auditor Agent")
    recommendation_note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

#### 2. Model `PrematureScalingAlert` (Cảnh Báo Vi Phạm Hàng Rào Quy Chuẩn):
```python
class PrematureScalingAlert(Base):
    __tablename__ = "premature_scaling_alerts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    current_stage: Mapped[str] = mapped_column(String(50))
    rule_code: Mapped[str] = mapped_column(String(100)) # E.g., NO_PAID_ADS_IN_S1, NO_SALES_HIRE_IN_S2
    severity: Mapped[str] = mapped_column(String(50), default="WARNING") # CRITICAL | WARNING | INFO
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

### 2.2. Schemas & Enums (`backend/app/founder_os/strategy/schemas/stage_gate_schemas.py`) [NEW]
* `AuditStatusEnum`: `APPROVED`, `CONDITIONALLY_APPROVED`, `REJECTED`.
* `AlertSeverityEnum`: `CRITICAL`, `WARNING`, `INFO`.
* `StageGateCriteriaItem`: `criterion_id`, `title`, `description`, `is_met`, `current_evidence_level`, `required_evidence_level`, `actual_metric`.
* `StageGateAuditRequest`: `project_id`, `target_stage`.
* `StageGateAuditResponse`: `id`, `project_id`, `from_stage`, `to_stage`, `readiness_score`, `audit_status`, `passed_criteria`, `missing_criteria`, `detected_risks`, `recommendation_note`.
* `PrematureScalingAlertResponse`: `id`, `project_id`, `current_stage`, `rule_code`, `severity`, `title`, `message`, `is_dismissed`.

---

### 2.3. Services Layer (`backend/app/founder_os/strategy/services/stage_gate_service.py`) [NEW]
* **`StageGateService`** cung cấp:
  1. **`evaluate_stage_readiness(db, workspace_id, project_id, target_stage)`:**
     - Lấy toàn bộ Hypotheses, Evidences, PESTEL signals, SWOT items, và Chiến lược của project.
     - So khớp với tiêu chí chuyển giai đoạn tương ứng ($S_0 \to S_1, S_1 \to S_2, \dots$).
     - Tính toán `readiness_score = passed_count / total_criteria`.
     - Phân loại `audit_status`:
       - `readiness_score >= 0.75` $\to$ `APPROVED`
       - `0.50 <= readiness_score < 0.75` $\to$ `CONDITIONALLY_APPROVED`
       - `readiness_score < 0.50` $\to$ `REJECTED`
     - Lưu kết quả vào `StageTransitionAudit`.
  2. **`check_anti_premature_guardrails(db, workspace_id, project_id)`:**
     - Quét các giả định, hành động và chi tiêu của dự án.
     - Phát hiện vi phạm:
       - Nếu Stage $\le S_2$ mà có chiến dịch "Paid Marketing Scale" $\to$ Alert `CRITICAL: Chi tiền quảng cáo trước khi đạt Problem/Solution Fit`.
       - Nếu Stage $\le S_3$ mà có kế hoạch "Enterprise Scale Governance" $\to$ Alert `WARNING: Over-engineering vận hành`.
     - Lưu và trả về danh sách `PrematureScalingAlert`.
  3. **`apply_stage_advancement(db, workspace_id, audit_id)`:**
     - Nếu audit được `APPROVED` hoặc `CONDITIONALLY_APPROVED`, cập nhật `project.project_stage = to_stage`.
     - Ghi nhận `StrategicDecision` tự động vào Company Memory.

---

### 2.4. API Router (`backend/app/founder_os/strategy/routers/stage_gate_router.py`) [NEW]
* `POST /api/v1/strategy/stage-gate/audit`: Thực hiện phiên thẩm định chuyển giai đoạn.
* `GET /api/v1/strategy/stage-gate/history/{project_id}`: Lịch sử các lần thẩm định.
* `GET /api/v1/strategy/stage-gate/guardrails/{project_id}`: Quét và lấy danh sách cảnh báo Anti-Premature.
* `POST /api/v1/strategy/stage-gate/apply-transition/{audit_id}`: Áp dụng chuyển giai đoạn chính thức.

---

## 3. CHI TIẾT THIẾT KẾ KỸ THUẬT FRONTEND (FLUTTER)

### 3.1. Data Models & Services (`frontend/lib/data/models/stage_gate_model.dart` & `stage_gate_service.dart`)
* `StageGateCriteriaModel`, `StageGateAuditModel`, `PrematureAlertModel`.
* `StageGateService`: Tương tác REST API với Backend.

---

### 3.2. UI Components & Dialogs (Flutter)
1. **`StageGateAuditModal` (`frontend/lib/modules/hologram_hub/widgets/stage_gate/stage_gate_audit_modal.dart`) [NEW]**:
   - Modal thẩm định chuyển giai đoạn:
     - Gauge vòng tròn hiển thị `Readiness Score %`.
     - Trạng thái thẩm định: Badge xanh `ĐỦ ĐIỀU KIỆN CHUYỂN STAGE`, vàng `ĐỦ ĐIỀU KIỆN CÓ ĐIỀU KIỆN`, đỏ `CHƯA ĐẠT (RETAIN STAGE)`.
     - Tab 1: **Tiêu chí Đạt (${passed.length})** kèm icon check xanh.
     - Tab 2: **Tiêu chí Thiếu (${missing.length})** kèm hướng dẫn hành động bổ sung.
     - Tab 3: **Cảnh Báo Rủi Ro Premature** (nếu có).
     - Nút bấm **"Xác Nhận Nâng Cấp Stage"** (chỉ active khi approved).
2. **`PrematureAlertBanner` (`frontend/lib/modules/hologram_hub/widgets/stage_gate/premature_alert_banner.dart`) [NEW]**:
   - Banner cảnh báo nổi bật gắn ở đầu Hologram Hub khi phát hiện hành vi mở rộng sớm.
3. **Nút "Thẩm Định Chuyển Stage"**:
   - Gắn trực tiếp vào `StageSelectorHeader` và `StagePolicyDialog`.

---

## 4. KẾ HOẠCH KIỂM THỬ (VERIFICATION PLAN)

### 4.1. Automated Backend Tests (`backend/app/tests/test_stage_gate_engine.py`)
- `test_stage_gate_evaluation_s1_to_s2_rejected_insufficient_evidence()`: Test chặn chuyển S1 sang S2 khi chưa đủ bằng chứng.
- `test_stage_gate_evaluation_s1_to_s2_approved_with_high_evidence()`: Test duyệt chuyển giai đoạn khi đã đạt điểm bằng chứng.
- `test_anti_premature_guardrail_detection()`: Test phát hiện vi phạm chi tiêu/mở rộng sớm ở S1/S2.
- `test_apply_stage_advancement_updates_project()`: Test cập nhật project stage và ghi vào Company Memory.

### 4.2. Automated Frontend Tests (`frontend/test/stage_gate_test.dart`)
- Test parsing models `StageGateAuditModel`, `PrematureAlertModel`.
- Test render widget `StageGateAuditModal` với Gauge %, tiêu chí đạt/chưa đạt.
- Test render widget `PrematureAlertBanner`.

---

## 5. CHECKLIST CÁC FILE SẼ TRIỂN KHAI TRONG PHASE 4

### Backend:
- [ ] `backend/app/founder_os/strategy/models.py` [MODIFY] (Thêm `StageTransitionAudit`, `PrematureScalingAlert`)
- [ ] `backend/app/founder_os/strategy/schemas/stage_gate_schemas.py` [NEW]
- [ ] `backend/app/founder_os/strategy/services/stage_gate_service.py` [NEW]
- [ ] `backend/app/founder_os/strategy/routers/stage_gate_router.py` [NEW]
- [ ] `backend/app/founder_os/strategy/router.py` [MODIFY]
- [ ] `backend/app/tests/test_stage_gate_engine.py` [NEW]

### Frontend:
- [ ] `frontend/lib/data/models/stage_gate_model.dart` [NEW]
- [ ] `frontend/lib/data/services/stage_gate_service.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_gate/stage_gate_audit_modal.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_gate/premature_alert_banner.dart` [NEW]
- [ ] `frontend/lib/modules/hologram_hub/widgets/stage_selector_header.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` [MODIFY]
- [ ] `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` [MODIFY]
- [ ] `frontend/test/stage_gate_test.dart` [NEW]
