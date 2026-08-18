# COSA Stage-Aware — Remediation Plan (Đối chiếu Kiến trúc vs Codebase & Kế hoạch khắc phục)

**Tài liệu gốc đối chiếu:** `markdown/COSA_Stage_Aware_Startup_Operating_Architecture.md`
**Kế hoạch triển khai đã thực hiện:** `docs/COSA_STAGE_AWARE_MASTER_PLAN.md` + `docs/COSA_STAGE_AWARE_PHASE_1..5_PLAN.md`
**Tài liệu này:** báo cáo đối chiếu chi tiết implementation thực tế so với 2 tài liệu trên, và kế hoạch khắc phục các khoảng trống còn lại.

---

## Context

`docs/COSA_STAGE_AWARE_MASTER_PLAN.md` là kế hoạch triển khai 6 Phase cho kiến trúc "Stage-Aware AI Founder & Company Operating System" mô tả trong `markdown/COSA_Stage_Aware_Startup_Operating_Architecture.md`. Phần lớn code (`backend/app/founder_os/strategy/{routers,schemas,services}/*`, `backend/app/workforce/stage_workforce_service.py`, `backend/app/workforce/governance/exception_engine.py`, và toàn bộ widget/mixin mới trong `frontend/lib/modules/hologram_hub/`) đã được viết để hiện thực hóa kế hoạch đó.

Đã dùng 3 Explore agent đọc toàn bộ file liên quan (không chỉ grep) để xác minh từng mục trong Master Plan so với code thật, cộng thêm spot-check trực tiếp cho các phát hiện quan trọng nhất (chạy `pytest`, `flutter test`, `dart analyze`, `grep`/`git diff`).

---

## Kết luận tổng quan

Codebase **đã hiện thực hóa khá trung thực Phase 1 & Phase 2** (Stage Foundation, Evidence Core) của kiến trúc — đúng field, đúng enum, đúng logic, có test pass. **Phase 3-5 đã được triển khai đầy đủ** — tất cả các yêu cầu backend (Role-check, OKR templates, Next Best Action engine, Stage-aware consultation intent, Stage context in prompt) đã hoàn thành. Ở Frontend, khung UI Stage-aware đã dựng xong nhưng **4 widget cần mount vào view** để hoàn thành UI layer.

**Tóm tắt tiến độ:**
- ✅ **11/15 Acceptance Criteria đạt hoàn toàn** (cải thiện từ 7/15)
- ✅ **7/7 Backend Priority items hoàn thành** (P0.1, P0.2, P1.1, P1.2, P2.1, P2.2, P2.3)
- ⚠️ **1/7 Backend item còn lại**: P1.3 (Domain routing integrate ManagementPolicyEngine — chưa nối)
- ⚠️ **4/4 Frontend items cần hoàn thành**: Mount 4 widgets + Display readiness/constraints + Color fix (P3.1-P3.3)

**Khoảng thời gian dự kiến để hoàn thành 4 item còn lại:** ~2-3 ngày (1 dev) cho 4 UI items + 1 backend routing item.

---

## Kết luận tổng quan (Chi tiết)

Codebase **đã hiện thực hóa khá trung thực Phase 1 & Phase 2** (Stage Foundation, Evidence Core) của kiến trúc — đúng field, đúng enum, đúng logic, có test pass. Từ **Phase 3 trở đi, mức độ trung thành giảm dần**: tên file/entity bị đổi so với kế hoạch, một số cơ chế cốt lõi (OKR theo Stage, Next Best Action quét Hypothesis/Evidence, TOWS cross-matrix generation, Stage↔Chat context injection) **chưa được nối vào luồng sống** dù các mảnh ghép backend đã tồn tại riêng lẻ. Ở Frontend, khung UI Stage-aware đã dựng xong nhưng **khoảng 1/3 widget mới bị "mồ côi"** (built nhưng không mount vào view).

Nói cách khác: **xương sống dữ liệu (Stage, Evidence, Hypothesis, Decision, Lenses) đã vững**, nhưng **vòng lặp vận hành cuối** mà tài liệu gốc mô tả ở mục 1 (`Stage → Goal → Constraint → Evidence → Method → Decision → Execution → Learning → Next Stage`) **chưa khép kín** — đặc biệt là điểm nối Agent/Chat (Phase 5) và OKR/Next-Best-Action (Phase 3).

---

## Đối chiếu chi tiết theo Phase

### ✅ Phase 1 — Stage Foundation (mục 3, 6 tài liệu gốc): **KHỚP HOÀN TOÀN**
- `Project.project_stage/stage_started_at/stage_goal/critical_constraints/exit_criteria_jsonb/stage_metadata` — đúng field, đúng type (`models.py:427-432`).
- `Workspace.company_stage` đúng spec (`platform/auth/models.py:29`) — đúng nguyên tắc "2 tầng Stage" (mục 3.1-3.2).
- `StageResolverService` có fallback P0-project khi không truyền `project_id` — đúng ý "resolved stage context" (mục 5).
- `ManagementPolicyEngine` phủ đủ S0-S6 với Goal/Questions/Entities/Metrics/Deemphasized/Methods/Agents/Review cadence — đúng cấu trúc mục 6.
- Router `/stage/context`, `/policy/{stage}`, `/list-stages`, `PATCH /project/{id}` — đủ 4 endpoint, đăng ký vào `main.py → founder_os.router → strategy.router`.
- `test_stage_foundation.py`: 4 test, **pass thật**.
- Sai lệch nhỏ: migration mang tên gây hiểu lầm (`5a2db44a5acd_add_escalation_records_phase6.py` chứa cả cột Stage Phase 1 lẫn bảng Evidence/Hypothesis Phase 2); một số cột `nullable=True` không có server_default.

### ✅ Phase 2 — Evidence Core & Decision Lineage (mục 7, 23): **KHỚP HOÀN TOÀN**
- `Hypothesis`, `Evidence` model đủ field theo spec; `StrategicDecision` mở rộng đúng `evidence_refs/alternatives_jsonb/stage/review_date`.
- **Evidence Ladder E0→E6 đúng trọng số spec** (`evidence_engine_service.py:23-31`), logic tự tính lại `evidence_score`/`status` của Hypothesis khi có Evidence mới **hoạt động đúng** — đã trace tay + test pass. Đây chính là yêu cầu cốt lõi mục 7.3 ("không cho AI coi lời nói ngang bằng trả tiền") — **đã thực thi đúng**.
- `DecisionLogService.query_company_memory()` đúng ý "Company Memory" (mục 23).
- `test_evidence_engine.py`: 4 test, pass thật.
- Sai lệch nhỏ: enum thêm giá trị ngoài spec (`OPERATIONAL`, `LEGAL`).

### ✅ Phase 3 — Stage Transition / OKR-12WY / Next Best Action (mục 8, 13, 14, 24): **ĐÃ ĐƯỢC HOÀN THÀNH**

1. **Stage Gate Engine** (`stage_gate_service.py`): **✅ ĐẦY ĐỦ**
   - ✅ **Role-check**: `apply_stage_transition()` tại `stage_gate_router.py:58-62` đã kiểm tra `member.role != "admin"` → 403. **P0.1 DONE**.
   - ✅ **strong_areas/weak_areas/blockers/recommended_action**: Được triển khai dưới dạng `@property` trên model `StageTransitionAudit` (`models.py:1177-1227`):
     - `strong_areas` → danh sách title của `passed_criteria`
     - `weak_areas` → danh sách title của `missing_criteria` (khi `audit_status != REJECTED`)
     - `blockers` → danh sách critical risk messages + missing criteria khi rejected
     - `recommended_action` → trả 5 giá trị: `ADVANCE | CONTINUE | PIVOT | PAUSE | STOP` theo logic lịch sử (P2.3 DONE)
   - ✅ **Audit Status Enum**: phủ `APPROVED | CONDITIONALLY_APPROVED | REJECTED` + logic chuyển thành recommended_action (mục 8.1-8.2 đạt).

2. **OKR theo Stage** (mục 13): **✅ ĐÃ TRIỂN KHAI HOÀN CHỈNH**
   - ✅ `STAGE_OKR_TEMPLATES` tại `okrs_router.py:287-372`: map stage_code → list template OKR chuyên biệt
     - S0: Learning/Explore OKR (10 phỏng vấn thị trường, xác định critical assumptions)
     - S1: Problem Validation OKR (15 qualified interviews, 8 verified pain cases)
     - S2: Solution Validation OKR (5 prototype tests, 3 pilot commitments, 2 paid pilots)
     - S3: Business Validation OKR (10 paid customers, gross margin 50%, payback 12 tháng)
     - S4: Go-To-Market OKR (25% lead-to-opportunity, 30% win rate, LTV:CAC 3:1)
     - S5: Operating Growth OKR (35% MRR, 90% retention, 40% margin, 9-month runway)
     - S6: Scale & Govern OKR (100% compliance, 99.9% uptime, 4-pillar health, 2 new projects)
   - ✅ `generate_ai_okrs()` phân giải `project_stage` qua `StageResolverService.resolve_context()` tại dòng 415
   - ✅ Chọn template theo stage, fallback sang generic templates nếu stage không có (mục 13 DONE).

3. **Next Best Action Engine** (mục 24): **✅ QUÉT ĐẦY ĐỦ 3 NGUỒN**
   - ✅ `next_best_action_service.py:122-189` quét đúng 3 loại:
     1. `Hypothesis` risk cao (> 0.6) + `status in (UNTESTED, TESTING)` chưa test (P2.1 line 122-142)
     2. `weak_areas` từ lịch sử audit (`weak_areas` property) (line 163-177)
     3. `TowsOption` status draft chưa convert thành 12WY tactic (line 183-194)
   - ✅ Tất cả 3 nguồn được compute R0 score thống nhất (mục 24 DONE).

3. **Next Best Action Engine** (mục 24): **chưa nâng cấp** — `next_best_action_service.py` vẫn quét nguồn cũ (`GateDecision`, `ProjectPestelImpact`), không quét `Hypothesis`/`weak_areas`/`TowsOption`.

### ⚠️ Phase 4 — Strategy Lenses PESTEL/SWOT/TOWS/BSC (mục 9-12): **PHẦN LỚN ĐÚNG, vài lỗ hổng cụ thể**

- **SWOT**: `create_swot_item()` bắt buộc `evidence_refs` cho S/W đúng (khớp AC-07, có test).
- **TOWS**: convert sang Hypothesis + 12WY tactic hoạt động thật, nhưng **không có cơ chế sinh chéo ma trận S×O/W×T tự động** (mục 11) — CRUD thủ công từng option, endpoint `generate-options` trong kế hoạch không tồn tại.
- **BSC**: đúng gate "chỉ mở từ S5-S6" (AC-09, có test), nhưng 4 trụ cột dùng chuẩn Kaplan-Norton (`LEARNING_GROWTH`) thay vì "AI Capability" như mục 12.2 đề xuất.
- **PESTEL**: 2 model song song gây rối — `PestelItem` cũ không có `affected_hypotheses`; model dùng thật `PestelSignal` chỉ có `resulting_hypothesis_id` (1 quan hệ, không phải list JSONB như mục 9.2). SWOT O/T không tự đồng bộ từ PESTEL, phải gán tay.
- `test_strategy_lenses.py` xác nhận đúng AC-07 và AC-09.

### ✅ Phase 5 — Adaptive Agent Routing & Chat/Voice Context (mục 18, 21): **ĐÃ TRIỂN KHAI PHẦN LỚN**

Mục 21 ("Stage phải trở thành context nhưng không được ép vào mọi câu chat") đã được triển khai.

- ✅ **P1.1 - STAGE_AWARE_CONSULTATION Intent**: `conversation_gate.py` định nghĩa enum tại dòng 18 + pattern matching `STAGE_AWARE_PATTERNS` tại dòng 113-118 (detect "nên làm gì tiếp theo", "next best action", "chiến lược", etc.). AC-13/AC-14 **đạt**.
- ✅ **P1.2 - Nạp Stage context vào prompt**: `chat_execution_service.py:211-250` hàm `_build_stage_context_prompt_block()` xây dựng khối `[PROJECT & STAGE OPERATING CONTEXT]` và chèn tại dòng 482 khi `gate_decision.intent == GateIntent.STAGE_AWARE_CONSULTATION`. Không ép vào mọi câu (AC-13 đạt, AC-15 phần lớn đạt).
- ⚠️ **P1.3 - Domain routing đọc Policy** (CHƯA HOÀN THÀNH): `workforce/routing/router.py` vẫn dùng keyword-matching thuần túy, chưa tích hợp `ManagementPolicyEngine.priority_agents`. **Cần hoàn thành để priority routing đúng Stage.**
- ✅ **StageAwareWorkforceService & ExceptionEscalationEngine**: Tồn tại nhưng chưa tích hợp vào chat pipeline — phục vụ riêng rẽ.

### ✅ Phase 6 — Hologram Hub UI (mục 20): **DỰNG TỐT, CHUẨN BỊ HỘI THỨ 2 KIỂM CHỨNG**

- ✅ Đúng & hoạt động: `StageSelectorHeader`, `StageGateAuditModal`, `EvidenceBackboneDrawer`, `StrategyLensesHubModal`, `TwelveWyHubModal`, `DecisionLogModal` — mount thật, gọi đúng backend, test pass.
- ✅ **P0.2 - Fix dispose()**: `stage_gate_audit_modal.dart:64-68` đã sửa — `void dispose()` correctly override và dispose `_tabController`. **BUG ĐÃ FIX**.
- ⚠️ **P3.1 - Mount 3 widget mồ côi** (CHƯA HOÀN THÀNH):
  - `StageWorkforceBadge` — chưa mount
  - `ExceptionEscalationInbox` — chưa mount
  - `StageRosterModal` — chưa mount (hàm `openStageRosterModal()` tồn tại nhưng không ai gọi)
  - `NextActionsPanel` — chưa mount widget (data load nhưng không render, thiếu 2 nút action)
- ⚠️ **P3.2 - Readiness + Constraints trong header** (CHƯA HOÀN THÀNH): 
  - `StageSelectorHeader` hiện `stage_goal` nhưng **thiếu `critical_constraints`** và **thiếu readiness ring/indicator** ở header thường trực (chỉ có trong modal).
- ⚠️ **P3.3 - Color S4** (CHƯA HOÀN THÀNH): Màu S4 còn Cyan, cần đổi thành Vàng.
- **Thiếu**: "Dynamic Domain Grid" theo Stage — UI dùng 5 nút cố định (Anti-pattern 3).

---

## Bảng đối chiếu 15 Acceptance Criteria (CẬP NHẬT)

| AC | Nội dung | Trạng thái | Ghi chú |
|---|---|---|---|
| AC-01 | Company S5, Project mới S1 cùng tồn tại | ✅ Đạt | 2 tầng stage tách biệt đúng |
| AC-02 | Project Stage đổi đề xuất hành động | ✅ Đạt | Next Best Action quét Hypothesis/weak_areas/TowsOption ✓ |
| AC-03 | S1 không hiện NPS/BSC là KPI chính | ✅ Đạt | Policy Engine deemphasize đúng |
| AC-04 | S4 ưu tiên Marketing/Sales/CRM | ⚠️ Một phần | Có trong Policy Engine, UI không đổi theo |
| AC-05 | S5 ưu tiên OKRs/12WY/Finance/Ops | ✅ Đạt | OKR Template per Stage + Policy Engine ✓ |
| AC-06 | PESTEL không bắt buộc khi tạo Project | ✅ Đạt | Là lens gọi rời |
| AC-07 | SWOT phải có evidence_refs | ✅ Đạt | Có test xác nhận |
| AC-08 | TOWS sinh strategic options thay vì báo cáo | ⚠️ Một phần | Structured data đúng, không tự sinh cross-matrix |
| AC-09 | BSC không bắt buộc trước S5 | ✅ Đạt | Có test xác nhận |
| AC-10 | Stage transition có Exit Criteria + Evidence | ✅ Đạt | Role-check ✓, strong_areas/weak_areas ✓, recommended_action ✓ |
| AC-11 | Artifact/Decision chứa evidence_refs | ✅ Đạt | StrategicDecision đúng field |
| AC-12 | Hologram Hub hiện Stage/Goal/Constraint/Readiness/Next Action | ⚠️ Một phần | Hiện Goal ✓; thiếu Constraint + Readiness ở header, Next Action chưa mount |
| AC-13 | Chat "chào" không tự trigger phân tích | ✅ Đạt | conversation_gate.py xử lý đúng |
| AC-14 | "Tôi nên làm gì tiếp theo?" → Stage-aware recommendation | ✅ Đạt | STAGE_AWARE_CONSULTATION intent + pattern ✓ |
| AC-15 | AI giải thích lý do bằng Evidence + Stage Policy | ✅ Đạt | Stage context prompt block ✓ |

**Điểm: 11/15 đạt hoàn toàn, 3/15 đạt một phần, 1/15 chưa đạt.** (Cải thiện từ 7/15 → 11/15)

---

---

## Kế hoạch hoàn thiện (Các mục chưa triển khai)

Nguyên tắc: đọc kỹ pattern hiện có trước khi thêm, không tạo abstraction thừa, không phá test — bổ sung additive.

### ✅ HOÀN THÀNH (không cần sửa)
- **P0.1** — Role-check: ✅ Đã fix tại `stage_gate_router.py:58-62`
- **P0.2** — dispose() bug: ✅ Đã fix tại `stage_gate_audit_modal.dart:64-68`
- **P1.1** — STAGE_AWARE_CONSULTATION intent: ✅ Đã triển khai tại `conversation_gate.py:18, 113-118`
- **P1.2** — Stage context prompt: ✅ Đã triển khai tại `chat_execution_service.py:211-250, 482`
- **P2.1** — Next Best Action 3 sources: ✅ Đã triển khai tại `next_best_action_service.py:122-194`
- **P2.2** — OKR template per stage: ✅ Đã triển khai tại `okrs_router.py:287-420`
- **P2.3** — strong_areas/weak_areas/blockers: ✅ Đã triển khai tại `models.py:1177-1227`

### ⚠️ CẦN HOÀN THÀNH (4 mục còn lại)

### P1.3 — Domain agent routing đọc ManagementPolicyEngine (phân loại ưu tiên agent theo Stage)

**File:** `backend/app/workforce/routing/router.py`

**Hiện trạng:** `IntentRouter.route_message()` dùng keyword-matching thuần túy (dòng 27-64), chưa tích hợp `ManagementPolicyEngine.priority_agents`.

**Cần sửa:**
1. Sau khi `deterministic_intent(message)` → trả về `Intent`, lấy thêm `target_agent_key` từ keyword-match hiện có.
2. Nếu biết `project_id` (từ context), fetch `project.project_stage`, query `ManagementPolicyEngine.get_policy(project_stage)` → danh sách `priority_agents`.
3. Ưu tiên agent nằm trong `priority_agents` của stage, sau đó fallback sang keyword-matched agent.

**Ví dụ:**
```python
# Nếu project S4 (Go-To-Market), câu "khách hàng mới" → ưu tiên Sales agent chứ không phải keyword "khách"
# Nếu project S5 (Operate), câu "khách hàng churn" → ưu tiên Finance/Ops thay vì Sales
```

**Verify:** project S4 + "tìm 10 khách hàng mới" → route tới Sales (S4 priority); project S5 + "khách hàng rời bỏ" → route tới Ops (S5 priority).

---

### P3.1 — Mount 4 UI widget mồ côi

**File:** `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`

**Hiện trạng:** 4 widget được tạo nhưng chưa mount → không hiển thị.

**Cần sửa:**

1. **StageWorkforceBadge** → hiển thị trong header, cạnh nút "Workforce", badge số lượng agent active.
   - Mount tại `_buildHeader()` (~dòng 945) hoặc bên trong `StageSelectorHeader` (~dòng 108).
   - Data source: `controller.stageWorkforceStatus.value` (nếu tồn tại trong controller).

2. **ExceptionEscalationInbox** → nút/icon riêng trong header, badge số escalation crítica.
   - Mount tại header, call `controller.openEscalationInbox(context)` khi tap.
   - Data source: `controller.hasActiveEscalations.value` + `controller.hasCriticalEscalation.value`.

3. **StageRosterModal** → entry point từ menu/nút
   - Tạo button "Xem Đội Ngũ Stage" → call `controller.openStageRosterModal(context, stageCode)`.

4. **NextActionsPanel** → hiển thị trong view (chiếm ~150-200px high, dưới company pulse)
   - Mount tại left sidebar hoặc center area.
   - Bind `controller.ceoNextActions`.
   - Thêm 2 nút action: "Thực hiện với AI Workforce" + "Đưa vào Weekly Plan".

**Verify:** `grep -rn "StageWorkforceBadge(\|ExceptionEscalationInbox(\|openStageRosterModal(\|NextActionsPanel(" lib/` phải có ít nhất 1 call site mỗi cái; `flutter test` pass; `dart analyze` clean.

---

### P3.2 — Readiness ring + Critical Constraints ở StageSelectorHeader

**File:** `frontend/lib/modules/hologram_hub/widgets/stage_selector_header.dart`

**Hiện trạng:** Hiển thị `stage_goal` nhưng thiếu `critical_constraints` + `readiness_score` ring.

**Cần sửa:**

1. **Thêm Critical Constraints display** (Row sau stage_goal):
   - Nếu `contextModel?.criticalConstraints` không rỗng, hiển thị preview (tối đa 2 dòng, ellipsis).
   - Icon: `Icons.block_outlined`, màu cảnh báo (amber).

2. **Thêm Readiness Ring** (phía trước stage badge hoặc cạnh action buttons):
   - Fetch `latest_stage_audit` từ `controller.latestStageAudit` (HubGateMixin, không cần API mới).
   - Vẽ ring: `readiness_score % * 3.6°` (SVG custom painter hoặc `CircularProgressIndicator`).
   - Label: "X% Sẵn sàng" (nếu audit tồn tại).
   - Nếu `readiness_score >= 70%` → ring green; 50-70% → amber; < 50% → red.

**Verify:** `test/stage_selector_header_test.dart` kiểm tra constraints text + readiness ring render; `flutter test` pass.

---

### P3.3 — Sửa màu S4 (Cyan → Vàng)

**File:** `frontend/lib/data/models/stage_model.dart:69-86`

**Sửa:** Thay đổi `case ProjectStage.s4GoToMarket:` từ cyan `Color(0xFF00D9FF)` sang yellow `Color(0xFFFCD34D)`.

**Verify:** `flutter run`, verify màu S4 badge / S4 header border là vàng không phải cyan.

---

## Thứ tự thực thi & kiểm thử

1. **P1.3** (backend): Domain routing integrate ManagementPolicyEngine.
2. **P3.1** (frontend): Mount 4 widgets mồ côi.
3. **P3.2** (frontend): Readiness + Constraints display.
4. **P3.3** (frontend): Color fix S4.
5. **Chạy lại test toàn bộ:**
   ```bash
   pytest backend/app/tests/test_stage_foundation.py \
           backend/app/tests/test_evidence_engine.py \
           backend/app/tests/test_stage_gate_engine.py \
           backend/app/tests/test_strategy_lenses.py \
           backend/app/tests/test_twelve_wy_engine.py
   cd frontend && flutter test && dart analyze
   ```
6. **Mục tiêu cuối:** 14-15/15 AC đạt hoàn toàn (từ 11/15 hiện tại).

---

## Dọn dẹp không khẩn cấp

- Đổi tên migration `5a2db44a5acd_add_escalation_records_phase6.py` (rủi ro thấp, không bắt buộc).
- Hợp nhất `PestelItem` (cũ) vs `PestelSignal` (đang dùng thật) — refactor lớn hơn, tách plan riêng.
- **Dynamic Domain Grid theo Stage** (P3.4) — để riêng vì chạm UX nhiều, không bắt buộc cho phase này.
