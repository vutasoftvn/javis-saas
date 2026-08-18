# COSA — STAGE-AWARE STARTUP & COMPANY OPERATING ARCHITECTURE
## MASTER IMPLEMENTATION PLAN (CHI TIẾT TOÀN BỘ 6 PHASES)

**Tài liệu:** Kế hoạch tổng thể và đặc tả kỹ thuật chi tiết cho toàn bộ 6 Phase chuyển đổi COSA thành Hệ điều hành Vận hành Doanh nghiệp & Startup theo Giai đoạn.
**Đường dẫn file:** `docs/COSA_STAGE_AWARE_MASTER_PLAN.md`

---

## MỤC LỤC TỔNG THỂ
1. [Triết Lý Kiến Trúc & Hai Tầng Ngữ Cảnh](#1-triết-lý-kiến-trúc--hai-tầng-ngữ-cảnh)
2. [Vòng Đời Chuẩn 7 Stage (S0 → S6)](#2-vòng-đời-chuẩn-7-stage-s0--s6)
3. [Bốn Khung Chiến Lược (Strategy Lenses)](#3-bốn-khung-chiến-lược-strategy-lenses)
4. [Chi Tiết Kế Hoạch Phase 1: Stage Foundation](#phase-1-stage-foundation-nền-tảng-phân-định-giai-đoạn)
5. [Chi Tiết Kế Hoạch Phase 2: Evidence Core & Decision Lineage](#phase-2-evidence-core--decision-lineage-trục-kiểm-chứng-bằng-chứng)
6. [Chi Tiết Kế Hoạch Phase 3: Stage-Aware Execution, Transitions & Next Actions](#phase-3-stage-aware-execution-transitions--next-actions)
7. [Chi Tiết Kế Hoạch Phase 4: Strategy Lenses Engine (PESTEL, SWOT, TOWS, BSC)](#phase-4-strategy-lenses-engine-4-ống-kính-chiến-lược)
8. [Chi Tiết Kế Hoạch Phase 5: Adaptive Agent Routing & Chat/Voice Context](#phase-5-adaptive-agent-routing--chatvoice-context)
9. [Chi Tiết Kế Hoạch Phase 6: Adaptive Hologram Hub (Flutter UI)](#phase-6-adaptive-hologram-hub-giao-diện-flutter-thích-ứng)
10. [Kế Hoạch Kiểm Thử & 15 Tiêu Chí Nghiệm Thu (Acceptance Criteria)](#10-kế-hoạch-kiểm-thử--15-tiêu-chí-nghiệm-thu)

---

## 1. TRIẾT LÝ KIẾN TRÚC & HAI TẦNG NGỮ CẢNH

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              COMPANY LEVEL                              │
│       Vision • Mission • Core Values • Total Runway • AI Workforce      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 Quản trị danh mục (Portfolio Management)
                                     │
      ┌──────────────────────────────┼──────────────────────────────┐
      ▼                              ▼                              ▼
┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│  PROJECT A   │              │  PROJECT B   │              │  PROJECT C   │
│  (Hotel AI)  │              │(Marketing Hub│              │(Finance Core)│
│  STAGE: S1   │              │  STAGE: S4   │              │  STAGE: S5   │
└──────┬───────┘              └──────┬───────┘              └──────┬───────┘
       │                             │                             │
       ▼                             ▼                             ▼
Management Policy             Management Policy             Management Policy
  (Problem Valid.)               (Go-to-Market)              (Operate & Grow)
```

1. **Company Level (Tầng Bản Sắc & Quản Trị Danh Mục):**
   - Lưu trữ: `Vision`, `Mission`, `Core Values` (trong `StrategyFoundation` & `CoreValue`), Tổng quỹ tiền mặt / Runway toàn công ty, Hạ tầng AI Workforce và Danh mục dự án (Portfolio).
   - `Company Stage`: Là mức độ trưởng thành của tổ chức (Organizational Maturity).
2. **Project Level (Tầng Vận Hành Sống Còn & Tạo Giá Trị Trọng Tâm):**
   - Mỗi Project (Sản phẩm/Venture) sở hữu một vòng đời riêng biệt gồm **7 Stage chuẩn (S0 → S6)**.
   - Toàn bộ cơ chế vận hành hàng ngày: Giả định (Hypothesis), Bằng chứng (Evidence), OKRs, 12 Week Year, Tactics, Next Best Action và Giao diện làm việc đều lấy **Project Stage làm trung tâm điều phối (Project-Centric)**.

---

## 2. VÒNG ĐỜI CHUẨN 7 STAGE (S0 → S6)

| Stage | Tên Giai Đoạn | Câu Hỏi Sống Còn | Trọng Tâm Quản Trị | Metrics Chính | Lenses / Công Cụ | Deemphasized (Chưa Cần) |
|---|---|---|---|---|---|---|
| **S0** | **Explore** | Có cơ hội đủ lớn và đáng để nghiên cứu không? | Assumption Map, Market Signals, Rủi ro sơ bộ | Số giả định critical, Feasibility signals | Market Research, PESTEL-lite | BSC, NPS, CRM, SOP, OKR phòng ban |
| **S1** | **Problem Validation** | Khách hàng có nỗi đau thật sự và đủ đau để giải quyết không? | Customer Discovery, Phỏng vấn ICP, JTBD, Bằng chứng vấn đề | Qualified interviews, Problem match rate, Pain severity | Interview Log, Learning OKRs | BSC, NPS, Paid Ads, Scale metrics |
| **S2** | **Solution Validation** | Giải pháp có tạo giá trị đủ để khách hàng cam kết/đổi hành vi? | Prototype, MVP, Value Proposition, Willingness-to-pay | Activation, Pilot commitments, Demo acceptance, Paid pilots | Lean Experiments, Pricing Test, Validation OKRs | BSC, Full CRM, NPS diện rộng |
| **S3** | **Business Validation** | Giải pháp có thể biến thành mô hình kinh doanh sống được không? | Revenue Model, Unit Economics, Bán thử nghiệm, Runway | Paid customers, Gross margin, CAC ban đầu, Payback | Unit Economics, Evidence-backed SWOT | BSC, SOP phức tạp |
| **S4** | **Go-to-Market** | Có cách tiếp cận và chuyển đổi khách hàng lặp lại được không? | Positioning, Channel Selection, Sales Funnel, CRM Pipeline | Lead-to-opp, Win rate, CAC/LTV, MRR, Churn | TOWS (sinh chiến lược kênh), CRM, Sales Playbook | BSC tổng thể |
| **S5** | **Operate & Grow** | Vận hành thế nào để ổn định, có lãi hoặc tăng trưởng bền vững? | OKRs, 12 Week Year, SOPs, Tự động hóa, Quản trị tài chính | Revenue, Margin, Retention, Productivity, Sức khỏe vận hành | 12WY Engine, Company Health (BSC Lens), SWOT/TOWS | - |
| **S6** | **Scale & Govern** | Làm sao mở rộng quy mô tổ chức mà không mất kiểm soát? | Portfolio, Phân quyền, Governance, Quản trị rủi ro | 4 trụ cột cân bằng (Financial, Customer, Process, Team) | Strategy Balance (BSC), Portfolio Matrix, Governance | - |

---

## 3. BỐN KHUNG CHIẾN LƯỢC (STRATEGY LENSES)

- **PESTEL Lens (External Signals):** Quét bắt tín hiệu môi trường ngoài tác động trực tiếp lên Giả định (`Hypothesis`) hoặc Rủi ro (`Risk`) của Project.
- **SWOT Lens (Evidence-Backed Snapshot):** Bắt buộc có `evidence_refs`. S/W lấy từ số liệu nội bộ; O/T lấy từ PESTEL Signals.
- **TOWS Lens (Strategy Option Generator):** Kết hợp S-O, W-T để sinh 1–3 phương án chiến lược (`strategy_options`) chuyển thành Experiment / Tactic 12WY.
- **BSC Lens (Company Health Scorecard):** Kích hoạt từ S5–S6 với 4 trụ cột cân bằng: Tài chính, Khách hàng, Vận hành, Năng lực AI.

---

## PHASE 1: STAGE FOUNDATION (NỀN TẢNG PHÂN ĐỊNH GIAI ĐOẠN)

### 1. Mục tiêu
Thiết lập toàn bộ hạ tầng nhận thức Stage ở tầng Backend, phân tách rạch ròi giữa **Company State** (Bản sắc, danh mục) và **Project State** (Vòng đời 7 Stage thực tế), đồng thời cung cấp `ManagementPolicyEngine` làm kim chỉ nam chính sách cho mọi module và Agent phía sau.

### 2. Các File Sửa Đổi & Tạo Mới
- **`backend/app/founder_os/strategy/models.py` [MODIFY]:**
  - Mở rộng model `Project` với các trường:
    - `project_stage`: `String(50)`, default=`S1_PROBLEM_VALIDATION`, index=True
    - `stage_started_at`: `DateTime`, default=`datetime.utcnow`
    - `stage_goal`: `Text`, nullable=True
    - `critical_constraints`: `JSONB`, default=`list`
    - `exit_criteria_jsonb`: `JSONB`, default=`dict`
    - `stage_metadata`: `JSONB`, default=`dict`
- **`backend/app/platform/auth/models.py` [MODIFY]:**
  - Mở rộng model `Workspace` với trường `company_stage`: `String(50)`, default=`S5_OPERATE_GROWTH`.
- **`backend/app/founder_os/strategy/schemas/stage_schemas.py` [NEW]:**
  - Định nghĩa Enums `ProjectStageEnum` (S0..S6).
  - Định nghĩa Pydantic Schemas: `StagePolicySpec`, `StageContextResponse`, `ProjectStageUpdateRequest`.
- **`backend/app/founder_os/strategy/services/stage_resolver_service.py` [NEW]:**
  - Phân giải context: Nạp thông tin Company Identity (Vision, Mission, Values) + Project Stage. Hỗ trợ fallback thông minh về Project P0 active khi không truyền `project_id`.
- **`backend/app/founder_os/strategy/services/management_policy_engine.py` [NEW]:**
  - Cung cấp từ điển chính sách chuẩn cho 7 Stage (S0: Explore → S6: Scale & Govern) gồm Goal, Questions, Entities, Metrics, Deemphasized Tools, Recommended Methods, Priority Agents, Review Cadence.
- **`backend/app/founder_os/strategy/routers/stage_foundation_router.py` [NEW]:**
  - Các endpoints API: `GET /context`, `GET /policy/{stage}`, `PATCH /project/{project_id}`, `GET /list-stages`.
- **`backend/app/founder_os/strategy/router.py` [MODIFY]:**
  - Đăng ký `stage_foundation_router`.

---

## PHASE 2: EVIDENCE CORE & DECISION LINEAGE (TRỤC KIỂM CHỨNG BẰNG CHỨNG)

### 1. Mục tiêu
Xây dựng trục xương sống kiểm chứng cho startup từ S0 đến S4: Quản lý Giả định (`Hypothesis`), Bằng chứng (`Evidence`) theo Thang đo **Evidence Ladder (E0 → E6)**, và gắn vết nguồn gốc bằng chứng (`evidence_refs`) vào mọi Quyết định & Artifact.

### 2. Các File Sửa Đổi & Tạo Mới
- **`backend/app/founder_os/strategy/models.py` [MODIFY]:**
  - **Tạo model `Hypothesis`:** `id`, `workspace_id`, `project_id`, `category` (customer, problem, solution, pricing, channel, revenue, cost, tech, legal), `statement`, `importance` (0-1), `uncertainty` (0-1), `risk_score` (0-1), `evidence_score` (0-1), `confidence` (0-1), `status` (UNTESTED, TESTING, SUPPORTED, CONTRADICTED, INVALIDATED), `evidence_refs` (JSONB), `experiment_refs` (JSONB), `next_action`.
  - **Tạo model `Evidence`:** `id`, `workspace_id`, `project_id`, `type` (interview, observation, behavioral, transaction, usage, campaign, financial, market_signal), `ladder_level` (E0_OPINION .. E6_SCALABLE_EVIDENCE), `source`, `claim_supported`, `strength` (weak/medium/strong), `direction` (supports/contradicts/neutral), `hypothesis_refs` (JSONB), `artifact_refs` (JSONB), `raw_payload` (JSONB).
  - **Mở rộng `StrategicDecision`:** Bổ sung `evidence_refs` (JSONB), `alternatives_jsonb` (JSONB), `stage` (String), `review_date` (DateTime).
- **`backend/app/founder_os/strategy/schemas/evidence_schemas.py` [NEW]:**
  - Schemas cho CRUD Hypothesis, Evidence, EvidenceLadder.
- **`backend/app/founder_os/strategy/services/evidence_engine_service.py` [NEW]:**
  - Định nghĩa trọng số Thang đo Evidence Ladder:
    - `E0_OPINION` = 0.0 (Ý kiến cảm tính)
    - `E1_STATED_INTEREST` = 0.2 (Khách hàng nói thích)
    - `E2_OBSERVED_PROBLEM` = 0.4 (Quan sát thấy nỗi đau thật)
    - `E3_BEHAVIORAL_COMMITMENT` = 0.7 (Cam kết thời gian/dữ liệu/dùng thử)
    - `E4_ECONOMIC_COMMITMENT` = 0.9 (Đặt cọc, trả tiền pilot)
    - `E5_REPEAT_BEHAVIOR` = 0.95 (Mua lại, gia hạn)
    - `E6_SCALABLE_EVIDENCE` = 1.0 (Số liệu lặp lại quy mô lớn)
  - Tự động cập nhật `evidence_score` và `status` của Hypothesis khi có Evidence mới.
- **`backend/app/founder_os/strategy/services/decision_log_service.py` [NEW]:**
  - Lưu vết và truy vấn "Bộ nhớ quyết định của Công ty" (Company Memory: `Decision -> Evidence -> Hypothesis`).
- **`backend/app/founder_os/strategy/routers/evidence_router.py` [NEW]:**
  - Endpoints quản lý Giả định, Bằng chứng, Decision Lineage.

---

## PHASE 3: STAGE-AWARE EXECUTION, TRANSITIONS & NEXT ACTIONS

### 1. Mục tiêu
Cấu hình hóa các module thực thi hiện có (OKRs, 12WY) theo Stage, xây dựng bộ máy chuyển giai đoạn (`StageTransitionEngine`) và cỗ máy gợi ý 1–3 hành động tối ưu (`NextBestActionEngine`).

### 2. Các File Sửa Đổi & Tạo Mới
- **`backend/app/founder_os/strategy/services/stage_aware_execution_service.py` [NEW]:**
  - Sinh template 12WY Cycle & OKRs theo từng Stage:
    - `S1 Cycle Template:` Learning OKRs (Interviews, Problem match rate, Pilot interest).
    - `S2 Cycle Template:` Validation OKRs (Prototype activation, Paid pilot commitments).
    - `S4 Cycle Template:` Acquisition OKRs (Repeatable channel, Funnel conversion, CAC).
    - `S5 Cycle Template:` Operating Growth OKRs (MRR, Retention, Margin, Productivity).
- **`backend/app/founder_os/strategy/services/stage_transition_service.py` [NEW]:**
  - Thuật toán tính điểm sẵn sàng (`StageReadiness`): Đánh giá Exit Criteria + tỷ lệ Giả định cốt lõi đã được validated.
  - Phân rã: `strong_areas`, `weak_areas`, `blockers`.
  - Đưa ra Recommendation: `ADVANCE | CONTINUE | PIVOT | PAUSE | STOP`.
  - Hàm `execute_transition()`: Cập nhật Stage khi Founder xác nhận duyệt.
- **`backend/app/founder_os/strategy/next_best_action_service.py` [MODIFY]:**
  - Nâng cấp cỗ máy đề xuất hành động: Quét qua (1) Blocker/Critical Hypotheses rủi ro nhất chưa có bằng chứng, (2) Điểm yếu từ Readiness report, (3) TOWS Options đã chọn.
  - Trả về đúng **1–3 Next Best Actions** có độ ưu tiên cao nhất kèm lý do rõ ràng.
- **`backend/app/founder_os/strategy/routers/stage_transition_router.py` [NEW]:**
  - Endpoints: `GET /readiness/{project_id}`, `POST /transition/{project_id}`, `GET /next-actions/{project_id}`.

---

## PHASE 4: STRATEGY LENSES ENGINE (4 ỐNG KÍNH CHIẾN LƯỢC)

### 1. Mục tiêu
Tái cấu trúc PESTEL, SWOT, TOWS, BSC thành 4 **Ống kính Chiến lược (Callable Strategy Lenses)** được kích hoạt đúng lúc theo nhu cầu của Stage, không bắt buộc tuần tự.

### 2. Các File Sửa Đổi & Tạo Mới
- **`backend/app/founder_os/strategy/models.py` [MODIFY]:**
  - `SwotItem`: Bổ sung `project_id`, `evidence_refs` (JSONB), `confidence`.
  - `PestelItem`: Bổ sung `affected_hypotheses` (JSONB), `impact_level`.
  - `TowsOption`: Bổ sung `tows_pairing`, `recommended_experiment`.
- **`backend/app/founder_os/strategy/services/strategy_lenses_service.py` [NEW]:**
  - **PESTEL Lens:** Nhận các `external_signals` (luật, AI, kinh tế) → Cập nhật rủi ro lên Giả định của Project.
  - **SWOT Lens:** Tổng hợp điểm mạnh/yếu từ Bằng chứng nội bộ của Project (`evidence-backed`) + Cơ hội/Thách thức từ PESTEL.
  - **TOWS Lens:** Kết hợp chéo ma trận SWOT để sinh ra các `strategy_options` đề xuất cho Founder lựa chọn, biến thành Hypothesis hoặc Weekly Tactic.
  - **BSC / Company Health Lens (S5 & S6):** Tính toán điểm số trên 4 trụ cột cân bằng (Tài chính, Khách hàng, Quy trình/Vận hành, Năng lực AI).
- **`backend/app/founder_os/strategy/routers/strategy_lenses_router.py` [NEW]:**
  - Endpoints: `POST /lenses/pestel/signals`, `GET /lenses/swot/{project_id}`, `POST /lenses/tows/generate-options`, `POST /lenses/tows/select-option`, `GET /lenses/company-health`.

---

## PHASE 5: ADAPTIVE AGENT ROUTING & CHAT/VOICE CONTEXT

### 1. Mục tiêu
Kết nối nhận thức Stage vào AI Workforce & Chat/LiveKit Voice để AI phản hồi thông minh, đúng tầm giai đoạn mà vẫn duy trì tương tác tự nhiên.

### 2. Các File Sửa Đổi & Tạo Mới
- **`backend/app/workforce/chat/conversation_gate.py` [MODIFY]:**
  - Phân loại Intent thông minh:
    - *Smalltalk / Casual / Tech Q&A:* Không nạp Stage Context, phản hồi tự nhiên.
    - *Strategic / Planning / Next Action / Project Advice:* Gán intent `STAGE_AWARE_CONSULTATION`.
- **`backend/app/workforce/chat/chat_execution_service.py` [MODIFY]:**
  - Khi có intent tư vấn chiến lược, tự động gọi `StageResolverService` nạp prompt context:
    ```markdown
    [PROJECT & STAGE OPERATING CONTEXT]
    Project: {project_title} | Stage: {stage_name} ({stage_code})
    Primary Goal: {stage_goal}
    Critical Constraints / Blockers: {critical_constraints}
    Readiness Score: {readiness_score}%
    Policy Guidance: Focus on {recommended_methods}. Deemphasize {deemphasized_tools}.
    Top 3 Next Actions: {next_actions}
    ```
- **`backend/app/workforce/chat/ai_router.py` [MODIFY]:**
  - Định tuyến câu hỏi về đúng Domain Agent chuyên trách theo Stage Policy (ví dụ: S1 ưu tiên Customer Agent, S3 ưu tiên Finance Agent, S4 ưu tiên Marketing/Sales Agent).

---

## PHASE 6: ADAPTIVE HOLOGRAM HUB (GIAO DIỆN FLUTTER THÍCH ỨNG)

### 1. Mục tiêu
Nâng cấp giao diện Hologram Hub trên Flutter thành trung tâm chỉ huy biến đổi linh hoạt theo Project Stage được chọn.

### 2. Các File Sửa Đổi & Tạo Mới
- **`frontend/lib/modules/hologram_hub/widgets/stage_header_widget.dart` [NEW]:**
  - Project Selector + Stage Badge màu nhận diện (S0: Xám, S1: Xanh dương, S2: Tím, S3: Cam, S4: Vàng, S5: Xanh lá, S6: Đỏ Ruby).
  - Thẻ tóm tắt: Current Goal, Critical Constraints.
  - Vòng tròn đo Readiness Score % kèm nút "Đánh giá chuyển Stage".
- **`frontend/lib/modules/hologram_hub/widgets/next_actions_widget.dart` [NEW]:**
  - Hiển thị 1–3 thẻ hành động ưu tiên cao nhất, lý do tại sao cần làm, kèm nút "Thực hiện với AI Workforce" hoặc "Đưa vào Weekly Plan".
- **`frontend/lib/modules/hologram_hub/widgets/dynamic_domain_grid.dart` [NEW]:**
  - Render thẻ nghiệp vụ theo Stage:
    - *S1:* Customer Discovery, Interview Logs, Problem Statements, Evidence Box.
    - *S2:* Value Proposition, MVP Spec, Pricing Experiments.
    - *S3:* Unit Economics, Sales Evidence, Cash & Runway.
    - *S4:* Marketing Channels, Sales Funnel, CRM Pipeline, TOWS Options.
    - *S5:* 12WY Cycle, OKRs Scoreboard, Company Health (BSC), SOPs, AI Workforce.
- **`frontend/lib/modules/hologram_hub/widgets/stage_readiness_modal.dart` [NEW]:**
  - Modal phân tích chi tiết Exit Criteria, Blockers và nút Founder duyệt chuyển Stage.
- **`frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart` [MODIFY]:**
  - Quản lý state: `selectedProjectId`, `currentStageContext`, `nextActionsList`, `readinessData`.
- **`frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` [MODIFY]:**
  - Ghép nối các widget mới thành Adaptive Dashboard hoàn chỉnh (Dark mode, Glassmorphism, Micro-animations).

---

## 10. KẾ HOẠCH KIỂM THỬ & 15 TIÊU CHÍ NGHIỆM THU

### Kế Hoạch Test Tự Động (Automated Tests)
```bash
# Phase 1: Policy Engine & Stage Resolver
pytest backend/app/tests/founder_os/test_stage_foundation.py

# Phase 2: Evidence Ladder & Hypotheses
pytest backend/app/tests/founder_os/test_evidence_engine.py

# Phase 3: Stage Transitions & Next Best Actions
pytest backend/app/tests/founder_os/test_stage_transition.py
pytest backend/app/tests/founder_os/test_next_best_action.py

# Phase 4: Strategy Lenses (PESTEL, SWOT, TOWS, BSC)
pytest backend/app/tests/founder_os/test_strategy_lenses.py

# Phase 6: Flutter UI Widgets
cd frontend && flutter test
```

### 15 Tiêu Chí Nghiệm Thu (Acceptance Criteria)
1. **AC-01:** Một Company có thể ở S5 trong khi một Project mới ở S1.
2. **AC-02:** COSA dùng Project Stage để thay đổi đề xuất hành động.
3. **AC-03:** S1 không hiển thị NPS/BSC như KPI chính.
4. **AC-04:** S4 ưu tiên Marketing/Sales/CRM.
5. **AC-05:** S5 ưu tiên OKRs/12WY/Finance/Operations.
6. **AC-06:** PESTEL không chạy bắt buộc khi tạo Project.
7. **AC-07:** SWOT item phải tham chiếu bằng chứng (`evidence_refs`).
8. **AC-08:** TOWS tạo strategic options thay vì tạo báo cáo mô tả.
9. **AC-09:** BSC không xuất hiện bắt buộc trước S5.
10. **AC-10:** Stage transition phải có Exit Criteria + Evidence.
11. **AC-11:** Artifact chiến lược và Quyết định (Decision) chứa `evidence_refs`.
12. **AC-12:** Hologram Hub hiển thị đầy đủ Stage, Goal, Constraints, Readiness, Next Actions.
13. **AC-13:** Chat câu chào xã giao không tự động trigger phân tích Stage.
14. **AC-14:** Câu hỏi "Tôi nên làm gì tiếp theo?" kích hoạt đề xuất Stage-aware chuẩn xác.
15. **AC-15:** AI giải thích được lý do đề xuất hành động dựa trên Bằng chứng & Chính sách Stage.
