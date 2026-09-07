# Kế hoạch legal applicability, authority và nghĩa vụ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng F15/F16; đánh giá pháp lý theo từng pháp nhân, approver đúng quyền và nghĩa vụ đi vào kế hoạch/review với bằng chứng hoàn tất.

**Architecture:** Reuse catalog/version/rule/obligation, deployment governance và compliance resolver hiện có. Company evaluate rule có kiểu; unknown/missing facts yêu cầu review, không tự coi exempt. Agent cung cấp hồ sơ/đề xuất; authority do code xác định.

**Tech Stack:** Encore/TypeScript/Drizzle, PostgreSQL, Flutter/GetX, Vitest và integration tests.

**Spec:** [07](/docs/architecture/overview/07-code-audit-business-agents-2026-09-05.md), [08](/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md), [plan tổng](/docs/superpowers/plans/2026-09-05-business-agents-master.md).

## Global Constraints

- Kế thừa plan tổng; authority mới phụ thuộc A2/A3. Không coi người tạo hồ sơ là founder có thẩm quyền.
- Rule/source ACCEPTED không đồng nghĩa áp dụng cho mọi doanh nghiệp hoặc implementation verified.
- Không sửa migration 14/25/28/30/31 đã áp dụng để “sửa dữ liệu”; thêm version/correction migration mới.
- Không tự nộp hồ sơ, ký hợp đồng hoặc kết luận tuân thủ từ câu trả lời model. Provider TT58/full-text mapping được kiểm ở F5.

## L1 — Enum thống nhất và applicability theo pháp nhân

**Files sửa:** [legal-applicability.service.ts](/services/company/finance-legal/services/legal-applicability.service.ts), [legal-obligation.service.ts](/services/company/finance-legal/services/legal-obligation.service.ts), [legal-entity-profile.service.ts](/services/company/finance-legal/services/legal-entity-profile.service.ts), [regulation-catalog.service.ts](/services/company/finance-legal/services/regulation-catalog.service.ts), [next-best-action.service.ts](/services/company/operations/strategy/services/next-best-action.service.ts), [shared enums](/shared/contracts/enums.json), [finance-legal schema](/services/company/shared/db/schema/finance-legal.ts).

**Files tạo:** [legal-predicate.ts](/services/company/finance-legal/services/legal-predicate.ts), [legal-applicability-integrity.test.ts](/services/company/finance-legal/tests/legal-applicability-integrity.test.ts), [32_legal_predicate_versions.up.sql](/services/company/finance-legal/migrations/32_legal_predicate_versions.up.sql).

**Schema:** applicability result có workspace_id/legal_entity_id/rule_version/facts_version/result/reason_codes/evaluated_at/source_ref; unique theo entity/rule/facts version. Predicate discriminated union chỉ hỗ trợ field/operator được định nghĩa; unknown operator trả NEEDS_REVIEW. Canonical entity VERIFIED; obligation instance OPEN/IN_PROGRESS/FULFILLED/EXEMPT/CANCELLED; overdue là derived từ dueAt và nonterminal status. Legacy PENDING của instance map OPEN tại migration/adapter đã xác minh, không đổi mọi bảng có PENDING.

**Interfaces:** `evaluateLegalPredicate(predicate,facts): "APPLIES"|"NOT_APPLIES"|"NEEDS_REVIEW"`; `listOpenObligations(ctx,{projectId?,legalEntityId?,at})` trả OPEN/IN_PROGRESS và overdue metadata; `evaluateEntityApplicability(ctx,legalEntityId,fiscalProfileId)` không dùng profiles[0].

- [ ] Test rule VERIFIED match pháp nhân A, entity B chưa verified không match; regime đúng/sai/thiếu; OPEN được action context lấy; unknown field NEEDS_REVIEW. Mẫu kiểu predicate:

```ts
export type LegalPredicate = {
  entityStatus?: "VERIFIED";
  accountingRegime?: string;
  fiscalYearStartOnOrAfter?: string;
};
export type LegalFacts = {
  entityStatus: string | null;
  accountingRegime: string | null;
  fiscalYearStart: string | null;
};
```

- [ ] Chạy `DBTEST company finance-legal/tests/legal-applicability-integrity.test.ts`; RED phải thể hiện literal cũ/profiles[0]/OPEN filter. Không bỏ assert vì seed đang review_pending; fixture phải chọn rule version đã review riêng cho test.
- [ ] Thêm migration correction: tạo version mới cho predicate status cũ đã biết, lưu supersedes/source/correction reason. Không tự active rule mà source đang review_pending. Backfill applicability per entity; missing regime/fiscal start giữ NEEDS_REVIEW, không false exempt.
- [ ] Evaluator AND giữa các điều kiện: missing field→NEEDS_REVIEW; khác giá trị đã biết→NOT_APPLIES; tất cả match→APPLIES. Date/enum parser reject malformed value. Adapter future composite predicates dùng schema explicit, không eval JS từ DB.
- [ ] Public handler bắt entityId hoặc trả kết quả theo từng entity; aggregate workspace chỉ tổng hợp kết quả có provenance. Test hai workspace/two entities và rerun idempotent; regenerate enum, typecheck/boundaries/migration gates. Commit `fix: evaluate legal obligations by canonical status and legal entity`.

## L2 — Authority thực của AI deployment và approval

**Files sửa:** [ai-compliance-governance.handler.ts](/services/company/finance-legal/handlers/ai-compliance-governance.handler.ts), [ai-compliance-governance.service.ts](/services/company/finance-legal/services/ai-compliance-governance.service.ts), [ai-compliance-access.service.ts](/services/company/finance-legal/services/ai-compliance-access.service.ts), [ai-compliance-snapshot.service.ts](/services/company/finance-legal/services/ai-compliance-snapshot.service.ts), [ai_compliance_controller.dart](/frontend/lib/modules/legal/controllers/ai_compliance_controller.dart), [compliance_center_panel.dart](/frontend/lib/modules/legal/views/widgets/compliance_center_panel.dart).

**Files tạo:** [deployment-authority.test.ts](/services/company/finance-legal/tests/deployment-authority.test.ts), [33_deployment_authority_versions.up.sql](/services/company/finance-legal/migrations/33_deployment_authority_versions.up.sql), [deployment_authority_test.dart](/frontend/test/features/compliance/deployment_authority_test.dart).

**Schema:** deployment phân biệt created_by_member_id, accountable_member_id, reviewer_member_id, approved_by_member_id, approved_version/policy_version; giữ founder_member_id cũ chỉ là legacy provenance, không dùng làm quyền. Approval mới gắn deployment version + assessment/source/compliance snapshot hash.

**Interfaces:** `createDeployment(ctx,input)` kiểm ai.deployment.create; `reviewDeployment(ctx,id,expectedVersion,evidenceRefs)` kiểm review; `approveDeployment(ctx,id,expectedVersion,approvalProof)` kiểm approve và rule rủi ro hiện tại. Request founderMemberId không được phép chỉ định authority; server resolve thành viên phù hợp.

- [ ] Regression test member có quyền create nhưng không approve tự tạo rồi duyệt phải bị chặn. Approver đúng quyền khác createdBy được phép nếu policy cho phép; assessment sửa sau review làm approval cũ invalid. Test self-approval founder đơn lẻ chỉ khi policy cho phép, không bắt mặc định hai người.
- [ ] Chạy `DBTEST company finance-legal/tests/deployment-authority.test.ts`; RED theo lỗ hổng F16. Invariant triển khai:

```ts
const decision = await authorizeBusinessAction(ctx, "ai.deployment.approve",
  {workspaceId: ctx.workspaceId, legalEntityId: deployment.legalEntityId},
  {resourceVersion: deployment.version, risk: deployment.riskTier});
if (decision.effect === "DENY") throw APIError.permissionDenied("Deployment approval denied");
```

REQUIRE_APPROVAL phải kiểm proof từ workflow hiện có; ALLOW vẫn cần assessment đầy đủ, version đúng và hard compliance floor. Không so ctx.memberId với một field caller tự đặt để kết luận quyền.
- [ ] Backfill legacy approver chỉ khi chứng minh membership/authority tại thời điểm approval; hồ sơ không đủ evidence→REVIEW_REQUIRED, giữ historical record. Không tự re-approve hàng loạt. Runtime snapshot invalidate khi deployment/assessment/policy version đổi, dùng resolver sẵn có.
- [ ] DTO trả allowedActions + responsible/reviewer/approver riêng; Flutter hiện “Người tạo”, “Người chịu trách nhiệm”, “Người duyệt” và lỗi thiếu quyền inline, không gọi tất cả là founder. FLUTTER test không thấy nút approve với create-only permission; direct API vẫn phải reject.
- [ ] Chạy compliance access/runtime tests, enum/contract gates, migration và Flutter tests; commit `fix: bind deployment approval to verified workforce authority`.

## L3 — Vòng đời nghĩa vụ, evidence và weekly review

**Files sửa:** [legal-obligation.service.ts](/services/company/finance-legal/services/legal-obligation.service.ts), [legal-obligation.handler.ts](/services/company/finance-legal/handlers/legal-obligation.handler.ts), [legal_service.dart](/frontend/lib/modules/legal/services/legal_service.dart), [legal_controller.dart](/frontend/lib/modules/legal/controllers/legal_controller.dart), [legal_view.dart](/frontend/lib/modules/legal/views/legal_view.dart), S4 project-action-context và weekly-review service.

**Files tạo:** [legal-obligation-lifecycle.test.ts](/services/company/finance-legal/tests/legal-obligation-lifecycle.test.ts), [34_obligation_lifecycle.up.sql](/services/company/finance-legal/migrations/34_obligation_lifecycle.up.sql), [obligation_flow_test.dart](/frontend/test/modules/legal/obligation_flow_test.dart).

**Schema:** obligation instance owner_member_id/legal_entity_id/rule_version/period_key/due_at/due_timezone/version; evidence relation và transition journal(actor/reason/from/to/source_version); unique(entity,rule,period_key) để retry scheduler không nhân nghĩa vụ. Dùng leaf UUID cho journal, giữ id instance hiện có.

**Contracts:** GET obligations filter entity/status/due range; POST transition nhận expectedVersion,toStatus,evidenceRefs,reason. FULFILLED cần evidence theo rule và quyền legal.obligation.manage; EXEMPT cần căn cứ applicability/exemption có source, không là nút bỏ việc. Reminder/escalation là in-app event/outbox có dedup key, không tự gửi email/Slack.

- [ ] Test tạo→OPEN→IN_PROGRESS→FULFILLED xuất hiện/biến mất khỏi active context đúng lúc; chưa có evidence không fulfill; overdue không làm mất nghĩa vụ khỏi danh sách. Các ngày luật cụ thể lấy từ rule/source đã review, test clock cố định, không hardcode deadline pháp lý không có nguồn.
- [ ] Chạy `DBTEST company finance-legal/tests/legal-obligation-lifecycle.test.ts`; RED trước bổ sung validation. Rule chuyển tối thiểu:

```ts
const allowed: Record<string, readonly string[]> = {
  OPEN: ["IN_PROGRESS", "FULFILLED", "EXEMPT", "CANCELLED"],
  IN_PROGRESS: ["FULFILLED", "EXEMPT", "CANCELLED"],
  FULFILLED: [], EXEMPT: [], CANCELLED: [],
};
```

Reopen là command tạo revision/instance hiệu chỉnh có reason và authority, không edit terminal history. All state changes CAS expectedVersion + workspace trong transaction, journal/outbox cùng commit.
- [ ] Tạo lịch obligation theo entity fiscal/calendar profile và timezone; missing facts→needs_review không đoán dueAt. Review tuần hiển thị due/overdue/owner/action/evidence; cam kết legal link obligationId theo S3; task done chỉ fulfill nếu evidence đúng rule.
- [ ] Flutter filter từng pháp nhân, assign owner, mở evidence/source/version, transition có lỗi inline. Test in-app reminder chỉ một lần mỗi rule/period/channel/event version và không lộ obligation workspace khác. FLUTTER obligation_flow_test, S4 context regression.
- [ ] Migration/typecheck/contract gates pass; commit `feat: track legal obligation evidence and weekly follow-through`.

**Nghiệm thu:** F15/F16 có test service/API; không silent exemption vì thiếu fact; mọi nghĩa vụ có entity/source/owner hoặc needs_review rõ; runtime và UI dùng cùng authority. Phần TT58 mapping thuế/sổ cụ thể do F5 kiểm chứng, không nhân bản evaluator pháp luật trong agent.
