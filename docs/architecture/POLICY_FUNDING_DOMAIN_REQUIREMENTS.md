# Policy Funding Domain — Requirement Capture (pre-deletion note)

**Ngày ghi nhận:** 2026-08-23. **Lý do:** domain này (`legacy/platform/platform_core/policy_funding/`,
20 bảng SQLAlchemy, không có consumer nào trong `services/company`/`services/cosa` — 2 service
TypeScript đang chạy thật) bị xoá theo Plan B (`docs/superpowers/plans/2026-08-23-company-business-schema-cleanup-plan-b.md`,
Task 6). Ghi lại đây trước khi xoá để không mất business intent nếu sau này cần port lại thật.

## Mục đích

Engine khớp nối (matching) startup Việt Nam với các chương trình hỗ trợ/tài trợ của chính phủ
(grant, voucher, tín dụng ưu đãi, hỗ trợ lãi suất...) — từ phát hiện nguồn văn bản pháp lý, đến
đánh giá điều kiện, nộp hồ sơ, giải ngân, và tuân thủ hậu tài trợ.

## Entity chính (nhóm theo luồng nghiệp vụ)

1. **Nguồn & xác minh chính sách:** `SourceDocument` (văn bản pháp lý gốc: luật, nghị định,
   thông tư, tài liệu hội thảo — có `verification_status` để phân biệt "nguồn nói gì" vs
   "COSA đã xác minh gì"), `SourceSnapshot` (snapshot nội dung thô phục vụ audit diff),
   `PolicyProgramClaim` (claim-based architecture: mệnh đề trích xuất từ tài liệu, tách biệt
   khỏi giá trị đã verify), `PolicyVerification` (nhật ký kiểm chứng bởi Founder/Admin),
   `AdminPolicyInbox` (hộp thư chính sách mới phát hiện chờ duyệt), `PolicyChangeProposal`
   (đề xuất thay đổi do AI phát hiện hoặc người đề xuất, chờ review trước khi áp dụng).
2. **Danh mục chương trình:** `PolicyProgram` (chương trình/quỹ/voucher/tín dụng — có target
   criteria: company_types, project_stages, trl_min, industries; financials: funding_min/max,
   matching_fund_pct, eligible_costs), `ProgramRound` (đợt tiếp nhận hồ sơ), `EligibilityRule`
   (quy tắc HARD/SOFT theo category LEGAL/TECH_TRL/FINANCIAL/IP/MARKET/TEAM, có field_path +
   operator để evaluate động).
3. **Đánh giá dự án:** `ProjectStageAssessment` (company_type + stage của project, có AI-suggested
   + founder-confirmed), `TrlAssessment` (TRL 1-9 hiện tại/mục tiêu, gắn evidence artifact),
   `FundingNeed` (nhu cầu vốn theo category CASH/CLOUD_CREDIT/INFRASTRUCTURE/VOUCHER/ADVISORY/IP_FILING).
4. **Matching & hồ sơ:** `ProjectProgramMatch` (kết quả khớp — 3 dimension riêng biệt:
   eligibility_status, match_score, readiness_score; pipeline_stage từ DISCOVERED đến COMPLETED),
   `EligibilityEvaluation` (chi tiết pass/fail từng rule), `MissingRequirement` (điều kiện/minh
   chứng còn thiếu, có thể link sang `operating.tasks` để founder xử lý trong 12WY),
   `Application` (hồ sơ ứng tuyển), `ApplicationSection` (từng phần thuyết minh: BACKGROUND,
   OBJECTIVES, TECHNOLOGY, TRL, OUTPUT_KPIS, WORK_PLAN, COMMERCIALIZATION, BUDGET, TEAM, IP, RISKS).
5. **Hậu tài trợ:** `FundingAward` (khoản đã duyệt/giải ngân — award_type, cash/non_cash,
   matching_required/actual), `ComplianceObligation` (nghĩa vụ báo cáo sau tài trợ),
   `CostAllocation` (phân bổ chi phí — mục đích chính: "Double Funding Guard", chống khai trùng
   chi phí giữa nhiều nguồn tài trợ khác nhau).

## Business rule quan trọng (nếu port lại, đừng bỏ sót)

- **Claim vs Verified tách biệt:** dữ liệu chính sách luôn đi qua 2 lớp — "nguồn tài liệu nói gì"
  (`PolicyProgramClaim`, `source_claim`, `claimed_values_jsonb`) và "COSA/founder đã xác minh gì"
  (`verification_status`, `PolicyVerification.result_status`). Không publish thẳng claim chưa
  verify vào matching catalog (`publish_to_matching` gate trên `PolicyProgram`).
- **3 dimension đánh giá match độc lập:** `eligibility_status` (đủ điều kiện cứng chưa),
  `match_score` (mức độ phù hợp), `readiness_score` (project đã sẵn sàng nộp hồ sơ chưa) —
  không gộp thành 1 điểm số duy nhất, vì founder cần biết "không đủ điều kiện" khác với
  "đủ điều kiện nhưng project chưa sẵn sàng".
- **Double Funding Guard:** `CostAllocation` tồn tại chuyên để cảnh báo một hạng mục chi phí
  (work_package + cost_category) bị khai trùng ở nhiều `FundingAward`/`Application` khác nhau —
  đây là yêu cầu compliance, không phải tiện ích phụ.
- **EligibilityRule là data-driven, không hardcode:** `field_path` + `operator` (GTE/LTE/EQ/IN/
  CONTAINS/EXISTS) + `expected_value_jsonb` cho phép thêm rule mới mà không cần deploy code —
  nếu port lại, giữ nguyên thiết kế này thay vì hardcode từng rule theo chương trình.

## Vì sao xoá thay vì port

Không có consumer nào ở `services/company`/`services/cosa` (2 service Encore.ts đang chạy thật) —
routers (`policy_catalog_router.py`, `admin_policy_router.py`, `application_router.py`,
`project_funding_router.py`) và services (`matching_service.py`, `proposal_service.py`,
`automation_service.py`) chỉ tồn tại trong `legacy/backend`, không được mount vào bất kỳ app
đang chạy nào. Nếu nhu cầu policy-funding-matching quay lại, port lại từ tài liệu này thay vì
từ code legacy — schema ở trên đã đủ để dựng lại từ đầu đúng ý định gốc.
