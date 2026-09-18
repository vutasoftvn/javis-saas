# Kế Hoạch Triển Khai: Tích Hợp CEO Advisor Skillpack & Mô Hình Điều Hành Cấp Cao vào COSA

**Ngày lập:** 2026-09-18  
**Tài liệu tham chiếu:** [`docs/agent/1-ceo.md`](file:///Volumes/SSD/javis-saas/docs/agent/1-ceo.md), [`docs/cosa.md`](file:///Volumes/SSD/javis-saas/docs/cosa.md), [`shared/contracts/executive-advisor-roles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json)  
**Trạng thái:** Chờ phê duyệt từ Founder (Planning Mode)

---

## 1. Tóm Tắt Mục Tiêu & Quyết Định Thiết Kế

Kế hoạch này nhằm chuẩn hóa và tích hợp tri thức điều hành từ [`docs/agent/1-ceo.md`](file:///Volumes/SSD/javis-saas/docs/agent/1-ceo.md) vào kiến trúc nền tảng của **COSA (javis-saas)**:
1. **Mô hình Phân cấp Điều hành Chuẩn (Command & Synthesis Hierarchy):**
   - **Founder / Co-founder / Manager (Con người):** Quyền lực tối cao, phê duyệt các quyết định lớn (`Human Founder Authority`), cấp quyền và quản trị Agent.
   - **CEO Agent (`cosa.executive.ceo`):** Tổng chỉ huy điều hành chiến lược / Cố vấn chiến lược cho Founder. Chịu trách nhiệm về Tầm nhìn (Vision), Chiến lược (Strategy), Phân bổ vốn (Capital Allocation), và Cây mục tiêu (`goals`). Sử dụng kỹ thuật suy luận **Tree of Thought (ToT)**.
   - **Chief of Staff Agent (`cosa.executive.chief_of_staff`):** Cánh tay phải điều phối quy trình (`Process & Deliberation Orchestrator`). Nhận chỉ đạo từ CEO/Founder để lập khung nghị sự, phân phối câu hỏi độc lập cho các C-Level, lọc nhiễu, tổng hợp trung thực (`Faithful Synthesis`) và đôn đốc tiến độ thực thi.
   - **Hội đồng Cố vấn Chuyên môn (C-Suite):** CFO, COO, CMO, CPO, CRO, CISO, VPE/CTO... phân tích độc lập (`PEER_DRAFT_FORBIDDEN`), đối chiếu bằng chứng xác thực (`EVIDENCE_MAPPING_REQUIRED`).
2. **Chuẩn hóa Skillpack COSA:** Chuyển đổi file đơn lẻ `1-ceo.md` thành package hoàn chỉnh tại `skillpacks/executive/ceo-advisor/` với `manifest.yaml` (chuẩn `agentos.ai/v1`), `SKILL.md` (chỉ dẫn điều hành), và bộ kiểm thử `evals/executive/ceo-advisor.yaml`.
3. **Tích hợp với Startup OS Core ([`docs/cosa.md`](file:///Volumes/SSD/javis-saas/docs/cosa.md)):** Nạp bối cảnh động từ view `v_current_company_context` (7 chiều Onboard) và cây mục tiêu `v_goal_tree` thay cho file tĩnh `company-context.md`.
4. **Xây dựng Tools/Capabilities chuẩn hóa:** Triển khai `StrategyAnalyzer` (ma trận trọng số) và `FinancialScenarioAnalyzer` (kịch bản Base/Bull/Bear) dưới dạng deterministic Python capabilities trong COSA.

---

## 2. Yêu Cầu Cần Founder Xem Xét (User Review Required)

> [!IMPORTANT]
> **Quyền Hạn Tối Đa Của CEO Agent:**
> Tuân thủ triệt để Quy tắc 1, 5, 8 trong `CLAUDE.md`: CEO Agent chỉ hoạt động ở mức trần tự trị **`L1_PROPOSE`** (chỉ đọc và đề xuất phương án). Mọi quyết định thay đổi trạng thái công ty, duyệt ngân sách, xoay trục chiến lược hoặc ban hành mục tiêu bắt buộc phải có xác nhận phê duyệt (Approval) từ Founder con người.

> [!NOTE]
> **Vị trí của CEO trong Executive Advisory Board:**
> Trong các phiên họp Hội đồng Cố vấn Điều hành (`executive-deliberation`), CEO có thể tham gia với tư cách:
> - **Chủ trì chiến lược (Lead Deliberator)** đưa ra đề bài và phương án sơ bộ, HOẶC
> - **Cố vấn chuyên môn độc lập** về phương hướng chiến lược để Chief of Staff tổng hợp chung với CFO/COO/CMO.
> Đề xuất cấu hình mặc định: CEO tham gia phân tích góc nhìn chiến lược vĩ mô, Chief of Staff tổng hợp đa chiều trình lên Founder.

---

## 3. Các Thay Đổi Đề Xuất (Proposed Changes)

### Vùng 1: Skillpack & Đánh Giá Chất Lượng (`skillpacks/` & `evals/`)

#### [NEW] [manifest.yaml](file:///Volumes/SSD/javis-saas/skillpacks/executive/ceo-advisor/manifest.yaml)
- Định nghĩa Skill theo chuẩn `agentos.ai/v1`:
  - `metadata.id`: `executive.ceo-advisor`
  - `metadata.name`: "CEO Strategic Leadership, Vision Alignment & Capital Allocation"
  - `capability.intents`: `ceo advisory`, `vision alignment`, `capital allocation`, `board prep`, `strategic trade-offs`, `tree of thought`
  - `autonomy.ceiling`: `L1_PROPOSE`, `side_effect_class`: `A`
  - `permissions.required`: `[READ_LOCAL]`
  - `applicability.project_stages`: từ `P0_DISCOVERY` đến `P6_SCALE_GOVERN`
  - `applicability.gates`: từ `G0` đến `G6`
  - `quality.eval_suite`: `evals/executive/ceo-advisor.yaml`

#### [NEW] [SKILL.md](file:///Volumes/SSD/javis-saas/skillpacks/executive/ceo-advisor/SKILL.md)
- Chuyển hóa và tinh chỉnh từ `1-ceo.md`:
  - **Mục tiêu vai trò:** Cố vấn chiến lược, phân bổ nguồn lực, mài giũa tư duy cho Founder.
  - **Quy tắc phân tích Tree of Thought (ToT):** Bắt buộc xây dựng tối thiểu 3 phương án cho các quyết định trọng yếu; đánh giá upside, downside, tính khả nghịch (reversibility) và hệ quả bậc hai.
  - **Stage-Adaptive Horizons:** Điều chỉnh tầm nhìn theo giai đoạn công ty (Seed: 3m–12m; Series A: 6m–2y; Scale: 1y–5y).
  - **Quy chuẩn phản hồi:** `Bottom Line ➔ Khuyến nghị cốt lõi (với độ tin cậy) ➔ Cơ sở dữ liệu ➔ Phương án hành động ➔ Đề xuất để Founder quyết định`.
  - **Gắn nhãn bằng chứng:** 🟢 Xác thực theo số liệu, 🟡 Trung bình, 🔴 Giả định.
  - **Nguyên tắc cấm side-effect:** Chỉ tư vấn và đề xuất, không tự động ghi dữ liệu hay thay đổi chính sách.

#### [NEW] [ceo-advisor.yaml](file:///Volumes/SSD/javis-saas/evals/executive/ceo-advisor.yaml)
- Bộ kiểm chuẩn tự động:
  - `accepts-governed-context`: Chấp nhận khi đủ `workspace_id` và `project_id`.
  - `missing-workspace`: Từ chối khi thiếu context workspace.
  - `cross-workspace`: Từ chối bằng chứng thuộc workspace khác.
  - `peer-draft-forbidden`: Từ chối nếu bị can thiệp bởi nháp của cố vấn khác.

---

### Vùng 2: Shared Contracts & Role Definitions (`shared/contracts/`)

#### [MODIFY] [executive-advisor-roles.json](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json)
- Bổ sung vai trò `ceo` vào danh mục `roles`:
  ```json
  {
    "key": "ceo",
    "label": "Chief Executive Officer / Strategic Advisor",
    "advisoryRemit": "Vision alignment, capital allocation, strategic trade-offs, board governance, stage-adaptive growth",
    "requiredProfileKey": "operations",
    "requiredAgentSpec": "cosa.executive.ceo",
    "requiredSkillPins": [
      "skillpack:executive/ceo-advisor@1.0.0"
    ],
    "advisoryOnly": true,
    "runtimeReadiness": "READY",
    "sourceProvenance": "superpowers:executive-advisory-board"
  }
  ```
- Thêm preset hoặc cập nhật preset hội đồng cố vấn nếu cần.
- Chạy code generator để cập nhật tự động:
  - `services/company/shared/contracts/executive-advisor-roles.generated.ts`
  - `apps/cosa/agents/executive_advisor_roles_generated.py`

---

### Vùng 3: Agent Platform Capabilities & Tools (`packages/agent/` & `apps/cosa/`)

#### [NEW] [strategy_analyzer.py](file:///Volumes/SSD/javis-saas/packages/agent/tools/strategy_analyzer.py) (hoặc capability trong `apps/cosa`)
- Deterministic Tool: Ma trận đánh giá phương án chiến lược bằng trọng số:
  - Input: Danh sách `options`, danh sách `criteria` (chi phí, độ phức tạp, tác động doanh thu, rủi ro) kèm `weights`.
  - Output: Điểm số chuẩn hóa (weighted scores), xếp hạng phương án, độ nhạy (sensitivity analysis).

#### [NEW] [financial_scenario_analyzer.py](file:///Volumes/SSD/javis-saas/packages/agent/tools/financial_scenario_analyzer.py)
- Deterministic Tool: Mô hình dự báo kịch bản tài chính:
  - Input: `current_cash`, `monthly_burn_rate`, `arr_growth_rate`, `forecast_months`.
  - Output: 3 kịch bản `Base`, `Bull`, `Bear` với số tháng runway, thời điểm cạn vốn (zero-cash date), và mốc thời gian cần gọi vốn (fundraising trigger date).

---

### Vùng 4: Tích Hợp Dữ Liệu Startup OS (`services/company` & `apps/cosa`)

#### [MODIFY] [executive_board_handler.py](file:///Volumes/SSD/javis-saas/apps/cosa/worker/executive_board_handler.py)
- Đảm bảo khi xử lý `role_key == 'ceo'`, runner tự động nạp snapshot bối cảnh 7 chiều mới nhất từ `v_current_company_context` và cây mục tiêu `v_goal_tree` nếu deliberation liên quan đến chiến lược / mục tiêu.

---

## 4. Kế Hoạch Xác Minh & Kiểm Thử (Verification Plan)

### Automated Tests
1. **Kiểm tra tính hợp lệ của Skillpack:**
   ```bash
   make skillpacks-validate
   ```
2. **Kiểm tra Gate toàn diện của repo:**
   ```bash
   make boundary-check
   make typecheck-py
   cd services/company && npm run typecheck
   ```
3. **Chạy Unit Test cho Contract & Spec Resolver:**
   ```bash
   source .venv/bin/activate && pytest tests/agent/executive_board/ -v
   ```
4. **Chạy Test cho Runner cô lập của Executive Board:**
   ```bash
   source .venv/bin/activate && pytest tests/agent/executive_board/test_runner_real_kernel_integration.py -v
   ```

### Manual Verification
1. Gọi API khởi tạo phiên nghị sự có vai trò CEO và Chief of Staff:
   - Kiểm tra CEO đưa ra phân tích độc lập với Tree of Thought (3 options).
   - Kiểm tra Chief of Staff tổng hợp chính xác quan điểm của CEO cùng các C-level khác thành bản tóm tắt đa chiều.
2. Kiểm tra không xảy ra hiện tượng Agent tự động kích hoạt thay đổi trái phép (chặn ở mức `L1_PROPOSE`).
