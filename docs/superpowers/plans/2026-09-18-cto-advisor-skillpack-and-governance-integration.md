# Kế Hoạch Triển Khai: Tích Hợp CTO Advisor Skillpack & Mô Hình Quản Trị Kỹ Thuật Lai vào COSA

**Ngày lập:** 2026-09-18  
**Tài liệu tham chiếu:** [`docs/agent/2-cto.md`](file:///Volumes/SSD/javis-saas/docs/agent/2-cto.md), [`https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/cto-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/cto-advisor), [`docs/cosa.md`](file:///Volumes/SSD/javis-saas/docs/cosa.md), [`shared/contracts/executive-advisor-roles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json)  
**Trạng thái:** Chờ phê duyệt từ Founder (Planning Mode - Chưa triển khai code)

---

## 1. Bối Cảnh & Phân Tích So Sánh

### 1.1. Hiện Trạng `docs/agent/2-cto.md` So Với Upstream Repo
- `docs/agent/2-cto.md` hiện tại là bản sao chép thô từ upstream `cto-advisor/SKILL.md`.
- File chứa metadata cũ của Claude-skills (`category: c-level`, `author: Alireza Rezvani`, `python-tools`), các đường dẫn tham chiếu chưa được cấu trúc vào hệ thống COSA (`scripts/tech_debt_analyzer.py`, `references/...`).
- Upstream repo gồm 3 thành phần chính:
  1. `SKILL.md`: Khung làm việc tổng thể cho CTO (Strategy, Team, Architecture, Vendor, Crisis).
  2. `references/`: 
     - `architecture_decision_records.md` (Quy chuẩn mẫu ADR, quy trình review và lưu trữ).
     - `engineering_metrics.md` (Khung DORA metrics, Engineering Health Dashboard).
     - `technology_evaluation_framework.md` (Ma trận Build vs Buy, Technology Radar).
  3. `scripts/`:
     - `tech_debt_analyzer.py` (Tính điểm nợ kỹ thuật theo 5 nhóm: Architecture, Code Quality, Infrastructure, Security, Performance; ưu tiên hành động theo công thức `(Severity × Blast Radius) / Cost-to-fix`).
     - `team_scaling_calculator.py` (Mô hình hóa chi phí tuyển dụng và quy mô đội ngũ kỹ sư).

### 1.2. Khoảng Lệch Kiến Trúc Với Nền Tảng COSA
1. **Triết Lý Vận Hành "Human-Light, Agent-Heavy":**
   - Upstream giả định mô hình kỹ thuật truyền thống với hàng chục kỹ sư con người (tỷ lệ Manager:IC 1:5–8, Senior:Junior 1:2, quy trình tuyển dụng con người cồng kềnh).
   - Trong COSA, nền tảng phục vụ cả Startup lẫn Large Enterprise vận hành theo mô hình **Đội ngũ Kỹ thuật Lai (Hybrid Engineering Workforce)**:
     - Số lượng kỹ sư con người tinh gọn (Lead Architects, Senior Reviewers giữ chốt chặn phê duyệt).
     - Hạm đội AI Coding Agents (tự động hóa viết code, sinh unit test, quét lint, refactor).
     - Trách nhiệm của CTO dịch chuyển mạnh sang: Kiến trúc Ngữ cảnh (Context/Prompt Architecture), Kiểm soát Nợ kỹ thuật do AI sinh ra (AI Slop / Hallucination Debt Prevention), Tối ưu hóa chi phí Token/Compute hạ tầng so với kết quả đạt được.
2. **Phân Định Vai Trò `cto` vs `vpe` Trong Hội Đồng Điều Hành:**
   - Codebase hiện có role `vpe` (`VP Engineering`, focus vào nhịp độ giao hàng, delivery pipeline, sprint backlog).
   - Cần bổ sung vai trò `cto` (`Chief Technology Officer`): Chịu trách nhiệm chiến lược công nghệ vĩ mô (3–5 năm), Kiến trúc hệ thống tổng thể (System Architecture), Chiến lược Build vs Buy vs Agent-Automate, Quản trị rủi ro nợ kỹ thuật và An ninh công nghệ.
3. **Cấu Trúc Mục Tiêu & Dữ Liệu Startup OS:**
   - Chưa kết nối với Cây mục tiêu lồng nhau (`goals`: Vision ➔ Strategic ➔ Tactical ➔ Sprint) và các chỉ số đo lường định lượng (`cosa_key_results`).
   - Chưa tích hợp view bối cảnh động `v_current_company_context` (7 chiều Onboarding) thay cho file tĩnh `company-context.md`.
4. **Quyền Lực & Giới Hạn Tự Trị (Governance):**
   - Phải tuân thủ trần tự trị **`L1_PROPOSE`** (`advisory-only`). CTO Agent chỉ đề xuất ADR, kiến trúc, kế hoạch xử lý nợ kỹ thuật và phân tích chi phí; con người (Founder/Lead Architect) giữ quyền quyết định cuối cùng.

---

## 2. Các Yêu Cầu Cần Founder Xem Xét (User Review Required)

> [!IMPORTANT]
> **1. Định Vị Phân Bổ `cto` và `vpe`:**
> - `cto` là Cố vấn Chiến lược Công nghệ & Kiến trúc (Strategic & Architectural Leadership).
> - `vpe` là Cố vấn Vận hành Phát triển & Nhịp độ Giao hàng (Delivery & Engineering Operations).
> - Cả hai đều thuộc Profile `coding` trong `startup-team-profiles.json`, nhưng có phạm vi trách nhiệm (`advisoryRemit`) và skillpack riêng biệt: `executive.cto-advisor` và `executive.vpe-advisor`.

> [!NOTE]
> **2. Tái Định Hình Bộ Công Cụ Scripts:**
> - `tech_debt_analyzer.py`: Sẽ được chuyển hóa thành module Python chuẩn hóa trong `packages/agent/executive_board/analyzers.py` (`TechDebtAnalyzer`), cho phép đánh giá nợ kỹ thuật theo tiêu chuẩn số liệu của COSA.
> - `team_scaling_calculator.py`: Thay vì chỉ tính số lượng con người, mở rộng thành **Hybrid Engineering Capacity Model** (kết hợp năng lực kỹ sư con người + năng lực hạm đội AI Coding Agents).

---

## 3. Các Thay Đổi Đề Xuất (Proposed Changes)

### Vùng 1: Skillpack Chuẩn Hóa (`skillpacks/executive/cto-advisor/`)

#### [NEW] [`skillpacks/executive/cto-advisor/manifest.yaml`](file:///Volumes/SSD/javis-saas/skillpacks/executive/cto-advisor/manifest.yaml)
- Định nghĩa Skill theo chuẩn `agentos.ai/v1`:
  - `metadata.id`: `executive.cto-advisor`
  - `metadata.name`: "CTO Technical Strategy, System Architecture & Hybrid Engineering Governance"
  - `capability.intents`: `["cto advisory", "technology strategy", "architecture decision", "tech debt governance", "build vs buy", "hybrid engineering workforce"]`
  - `autonomy.ceiling`: `L1_PROPOSE`, `side_effect_class`: `A`
  - `permissions.required`: `[READ_LOCAL]`
  - `applicability.project_stages`: từ `P0_DISCOVERY` đến `P6_SCALE_GOVERN`
  - `applicability.gates`: từ `G0` đến `G6`
  - `quality.eval_suite`: `evals/executive/cto-advisor.yaml`

#### [NEW] [`skillpacks/executive/cto-advisor/SKILL.md`](file:///Volumes/SSD/javis-saas/skillpacks/executive/cto-advisor/SKILL.md)
- Xây dựng lại toàn diện bằng Tiếng Việt (chuẩn thuật ngữ kỹ thuật quốc tế):
  - **Mục 1 - Persona & Authority:** Cố vấn công nghệ chiến lược cho Founder/Board; trần `L1_PROPOSE`.
  - **Mục 2 - 5 Trách nhiệm cốt lõi:**
    1. *Chiến lược công nghệ & AI (Technology & AI Strategy):* Tầm nhìn 3–5 năm, lộ trình kiến trúc, phân bổ 15–20% năng lực cho đổi mới/R&D.
    2. *Đội ngũ kỹ sư lai (Hybrid Engineering Team):* Đòn bẩy con người cao, quản trị hiệu suất kỹ sư kết hợp AI Coding Agents.
    3. *Quản trị kiến trúc (Architecture Governance & ADRs):* Khung quyết định kiến trúc, tiêu chuẩn hóa API/Data contracts.
    4. *Quản trị nợ kỹ thuật (Tech Debt Governance):* Phân loại P0–P3, công thức ưu tiên `(Severity × Blast Radius) / Cost-to-fix`.
    5. *Bảo mật hạ tầng & Đánh giá nhà cung cấp (Vendor & Security):* Build vs Buy vs Agentize, chi phí TCO 3 năm.
  - **Mục 3 - Bảy câu hỏi cốt tử của CTO:** Tập trung vào rủi ro sụp đổ hệ thống, nút thắt bus factor, tỷ lệ nợ kỹ thuật, đòn bẩy AI.
  - **Mục 4 - Bảng chỉ số kỹ thuật thích ứng (CTO Metrics Dashboard):**
    - DORA metrics (Deployment Frequency, Lead Time, Change Failure Rate, MTTR).
    - Chỉ số Đội ngũ lai: *AI Code Acceptance Rate*, *Compute/Token Spend per Feature*, *Human Review Bottleneck Ratio*.
    - Tech debt ratio (< 25%), System uptime (> 99.9%), API latency p95.
  - **Mục 5 - Cảnh báo đỏ (Red Flags):** Bùng nổ nợ kỹ thuật do AI sinh bừa bãi (AI slop debt); CTO là người duy nhất deploy; build time > 10m; chi phí cloud/AI tăng nhanh hơn doanh thu.
  - **Mục 6 - Phối hợp C-Suite:** CTO phối hợp với CEO, CPO, CFO, CISO, VPE, CHRO.
  - **Mục 7 - Kích hoạt chủ động (Proactive Triggers).**
  - **Mục 8 - Sản phẩm đầu ra (Output Artifacts):** Báo cáo Tech Debt, Hồ sơ ADR, Phân tích Build vs Buy, Dashboard sức khỏe kỹ thuật.
  - **Mục 9 - Kỹ thuật suy luận: ReAct & Evidence Mapping:** Phân tích bối cảnh, đối chiếu số liệu thực, chấm điểm tin cậy 🟢🟡🔴.
  - **Mục 10 - Tích hợp Startup OS:** Liên kết Cây mục tiêu `goals`, bối cảnh 7 chiều `v_current_company_context`.

#### [NEW] Các Cẩm Nang Tham Khảo Trong `skillpacks/executive/cto-advisor/references/`:
- `references/architecture_decision_records.md`: Mẫu ADR chuẩn, quy trình đề xuất, phản biện và lưu trữ phiên bản.
- `references/engineering_metrics.md`: Khung đo lường DORA kết hợp chỉ số hiệu quả kỹ thuật AI.
- `references/technology_evaluation_framework.md`: Ma trận Build vs Buy vs Agent-Automate, đánh giá rủi ro phụ thuộc vendor.

#### [NEW] [`evals/executive/cto-advisor.yaml`](file:///Volumes/SSD/javis-saas/evals/executive/cto-advisor.yaml)
- Bộ kiểm chuẩn tự động: Chặn rò rỉ workspace, kiểm soát trần tự trị L1_PROPOSE, ngăn chặn peer-draft contamination.

---

### Vùng 2: Hợp Đồng Vai Trò & Sinh Code (`shared/` & `scripts/`)

#### [MODIFY] [`shared/contracts/executive-advisor-roles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json)
- Bổ sung định nghĩa role `cto`:
  ```json
  {
    "key": "cto",
    "label": "Chief Technology Officer / Technical Strategy Advisor",
    "advisoryRemit": "Technology vision, system architecture, hybrid engineering workforce, tech debt governance, build vs buy evaluation",
    "requiredProfileKey": "coding",
    "requiredAgentSpec": "cosa.executive.cto",
    "requiredSkillPins": [
      "skillpack:executive/cto-advisor@1.0.0"
    ],
    "advisoryOnly": true,
    "runtimeReadiness": "READY",
    "sourceProvenance": "superpowers:executive-advisory-board"
  }
  ```

#### [EXEC] Sinh Code Tự Động:
- Chạy `node scripts/gen-executive-advisor-roles.mjs` để đồng bộ:
  - `services/company/shared/contracts/executive-advisor-roles.generated.ts`
  - `apps/cosa/agents/executive_advisor_roles_generated.py`

---

### Vùng 3: Analyzers & Agent Specs (`packages/agent/` & `apps/cosa/`)

#### [MODIFY] [`packages/agent/executive_board/analyzers.py`](file:///Volumes/SSD/javis-saas/packages/agent/executive_board/analyzers.py)
- Triển khai `TechDebtAnalyzer`:
  - Đánh giá 5 nhóm chỉ số: Architecture, Code Quality, Infrastructure, Security, Performance.
  - Tính điểm ưu tiên: `priority_score = (severity_weight * blast_radius) / cost_to_fix_days`.
  - Phân loại hành động theo Sprint: Immediate, Next Milestone, Tracked Backlog.
- Triển khai `BuildVsBuyAnalyzer`:
  - Ma trận trọng số 5 tiêu chí: Solves core problem, Migration risk, 3-year TCO, Vendor stability, Integration effort.
  - Đưa ra khuyến nghị định lượng kèm ngưỡng quy tắc (Rule of Thumb: Buy/Agentize unless Core IP).

#### [MODIFY] [`apps/cosa/agents/specs.py`](file:///Volumes/SSD/javis-saas/apps/cosa/agents/specs.py)
- Định nghĩa `COSA_EXECUTIVE_CTO_PROMPT` và `COSA_EXECUTIVE_CTO_AGENT_SPEC`.
- Đăng ký `cosa.executive.cto` vào từ điển `EXECUTIVE_AGENT_SPECS`.

---

### Vùng 4: Cập Nhật Tài Liệu Nguồn (`docs/agent/2-cto.md`)

#### [MODIFY] [`docs/agent/2-cto.md`](file:///Volumes/SSD/javis-saas/docs/agent/2-cto.md)
- Đồng bộ nội dung tài liệu thiết kế với phiên bản chuẩn hóa trong `skillpacks/executive/cto-advisor/SKILL.md`.

---

## 4. Kế Hoạch Kiểm Thử & Xác Thực (Verification Plan)

### Kiểm Thử Tự Động:
1. **Kiểm tra cú pháp & Schema Skillpack:**
   ```bash
   make skillpacks-validate
   ```
2. **Kiểm tra Hợp đồng Vai trò Sinh Tự Động:**
   ```bash
   node scripts/gen-executive-advisor-roles.mjs --check
   ```
3. **Unit Tests Bộ Phân Tích Kỹ Thuật (Analyzers & Specs):**
   - Viết mới `tests/agent/executive_board/test_cto_advisor_and_analyzers.py`:
     + Test phân tích nợ kỹ thuật: tính điểm đúng công thức, sắp xếp độ ưu tiên chính xác.
     + Test phân tích Build vs Buy: tính toán TCO và chấm điểm trọng số chuẩn xác.
     + Test Agent Spec của CTO: role mapping, advisory ceiling `L1_PROPOSE`, skill pin hợp lệ.
   - Chạy kiểm thử:
     ```bash
     .venv/bin/pytest tests/agent/executive_board/
     ```
4. **Kiểm tra Tính Toàn Vẹn Type & Lint:**
   ```bash
   npm --prefix services/company run typecheck
   npm --prefix services/cosa run typecheck
   make lint
   ```

---

## 5. Trạng Thái Thực Hiện
- [ ] Founder phê duyệt kế hoạch.
- [ ] Triển khai Skillpack `skillpacks/executive/cto-advisor/`.
- [ ] Cập nhật hợp đồng vai trò và sinh code.
- [ ] Triển khai Analyzers và Agent Spec.
- [ ] Chạy kiểm thử tự động và xác thực kết quả.
