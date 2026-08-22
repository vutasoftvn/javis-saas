# Phase 2 — Strategy & Startup Co-Founder Methodology domain

> Chi tiết thực thi cho Phase 2 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Viết mới hoàn toàn dựa trên `services/operations/` hiện có và guide kiến trúc mới — không dựa vào các tài liệu/ADR cũ khác làm authority. Đây là domain mới hoàn toàn ở `services/`, không phải port từ đâu.

## 2a. Tạo bounded context `services/operations/strategy/`

**Task:**
1. Tạo thư mục theo layering chuẩn §20 CLAUDE.md:
```
services/operations/strategy/
├── handlers/
├── services/
├── models/          # (nếu cần type riêng ngoài schema centralized)
└── tests/
```
2. Không tách thành `services/<new-service>` riêng — theo gate §18.2 của guide, domain này chưa đủ điều kiện tách microservice (chưa có lifecycle/data ownership khác biệt đủ lớn so với `operations/` hiện có).
3. Thêm README ngắn trong `services/operations/strategy/` mô tả bounded context: business flow `Project → Stage → Assumption → Experiment → Evidence → Gate → Decision → Next Best Action`.

**Acceptance:**
- [ ] Thư mục tồn tại đúng layering, có README mô tả flow.

## 2b. Schema & migration cho các entity còn thiếu

**Entity cần thêm** (thiết kế mới, field tối thiểu cho từng bảng — mở rộng thêm khi cần trong quá trình implement, không cần đủ 100% ngay từ đầu):

| Entity | Field cốt lõi |
|---|---|
| `stage_policies` | id, company_id, stage_key, requirements (jsonb), minimum_evidence_score, blocking_risk_rules (jsonb) |
| `stage_transitions` | id, company_id, from_stage, to_stage, policy_id, allowed (bool), created_at |
| `assumptions` | id, project_id, statement, importance (int), uncertainty (int), risk_score (computed), status |
| `experiments` | id, project_id, assumption_id, hypothesis, method, success_criteria, budget, owner_workforce_member_id, status |
| `evidence` | id, experiment_id?, project_id, source_type, claim, strength (0-1), confidence (0-1), supports_or_refutes |
| `interviews` | id, project_id, contact_ref (nullable, trỏ sang `commercial.contacts` qua id, không FK cứng cross-service), notes, conducted_at |
| `discovery_signals` | id, project_id, signal_type, payload (jsonb), source, created_at |
| `gate_evaluations` | id, project_id, stage_policy_id, requirements_met (bool), evidence_score, blocking_risks (jsonb), result, rationale, human_override (bool) |
| `decision_records` | id, project_id, gate_evaluation_id, decision, actor_workforce_member_id, evidence_snapshot (jsonb), created_at |
| `next_action_candidates` | id, project_id, source (enum: assumption/task/okr_gap/evidence/...), score (deterministic), rationale |
| `next_action_rankings` | id, project_id, candidate_id, rank, llm_rerank_note (nullable) |

Tất cả bảng: `company_id`, `workspace_id`, `created_at`, `updated_at`, `deleted_at` (soft-delete, theo pattern migration `2_align_schema.up.sql`).

**Task:**
1. Thêm định nghĩa Drizzle vào `services/shared/db/schema/strategy.ts` (file mới, theo đúng convention centralized schema hiện tại — không tạo `models/schema.ts` riêng trong `strategy/`).
2. Viết migration tương ứng trong `services/operations/migrations/` (số thứ tự tiếp theo sau migration hiện có gần nhất, kiểm tra bằng `ls services/operations/migrations/` trước khi đặt số).
3. Foreign key nội bộ trong cùng service (`project_id` trỏ `strategy.projects` đã có) dùng FK thật; tham chiếu cross-service (`commercial.contacts`) chỉ lưu id, không FK cứng (đúng nguyên tắc service boundary — mỗi service có DB schema riêng dù chung Postgres instance).
4. Index tối thiểu: `(company_id, workspace_id)`, `(project_id)` trên mọi bảng, `(assumption_id)` trên `experiments`, `(experiment_id)` trên `evidence`.

**Acceptance:**
- [ ] Toàn bộ 11 bảng tồn tại trong `strategy.ts` + migration chạy được (`encore db migrate` hoặc lệnh tương ứng repo dùng).
- [ ] Drizzle type generate không lỗi.
- [ ] Test tạo 1 record cho mỗi bảng qua Drizzle query trực tiếp (smoke test schema, chưa cần qua handler).

## 2c. Business logic tất định

**Task — viết service function trong `services/operations/strategy/services/`, mỗi function 1 file:**
1. `stage-assessment.service.ts`: input project context (task hiện tại, evidence hiện có) → output stage đề xuất + rationale, dựa rule tất định (ví dụ: chưa có evidence nào → stage sớm nhất; đã pass gate stage N → có thể ở stage N+1).
2. `assumption-ranking.service.ts`: rank assumption theo `importance × uncertainty`.
3. `experiment-proposal.service.ts`: từ top assumption chưa có experiment liên kết → đề xuất experiment mẫu (method/success_criteria placeholder do agent/skill điền sau, service chỉ tạo khung).
4. `evidence-scoring.service.ts`: chuẩn hoá `strength` về thang 0-1 theo `source_type` (interview > survey > 3rd-party data, ví dụ trọng số cụ thể do đội ngũ vận hành quyết định khi implement, không tự đặt số tuỳ tiện — để placeholder rõ ràng trong code với TODO nếu chưa có quyết định nghiệp vụ).
5. `gate-evaluation.service.ts`: input `stage_policy` + evidence hiện có của project → output `gate_evaluations` record (pass/fail + rationale), **không gọi LLM**.
6. `decision-recording.service.ts`: ghi `decision_records`, snapshot evidence tại thời điểm quyết định.
7. `next-best-action.service.ts`: sinh `next_action_candidates` từ nguồn tất định (stage hiện tại, assumption chưa giải quyết, evidence strength, task bị block ở `operations/`, OKR gap ở `operations/`) → tính `score` tất định → ghi `next_action_rankings`. **LLM chỉ được gọi ở bước rerank sau khi đã có ranking tất định, không được tự sinh candidate hay tự đặt priority** (ràng buộc cứng §5.2 guide gốc).

**Acceptance:**
- [ ] Mỗi service function có unit test với input/output cố định (không cần DB thật, test pure logic).
- [ ] Không service nào trong danh sách trên gọi model/LLM trực tiếp — nếu cần LLM rerank, đó là bước riêng ở tầng agent/skill (Phase 5), không nằm trong `services/`.
- [ ] `next-best-action.service.ts` cho cùng input luôn trả cùng thứ tự ranking (deterministic, có test reproduce).

## 2d. API handlers + domain event

**Task:**
1. Thêm handler CRUD tối thiểu cho từng entity ở `services/operations/strategy/handlers/` (POST create, GET list/get, PATCH update, DELETE = soft-delete set `deleted_at`).
2. Thêm `GET /operations/strategy/projects/:id/next-best-actions` — gọi `next-best-action.service.ts`.
3. Mọi handler dùng `TenantContext` (Phase 1a) để scope query theo `company_id/workspace_id`, dùng `APIError` chuẩn theo §20.4 CLAUDE.md.
4. Emit domain event khi write thành công: `ExperimentCreated`, `EvidenceRecorded`, `GateEvaluated`, `DecisionRecorded` (theo cơ chế event hiện có của `services/shared` nếu đã có, nếu chưa có event bus thì để dạng log có cấu trúc, ghi rõ TODO khi event bus thật được thêm ở phase khác).

**Acceptance:**
- [ ] Mọi endpoint có test tenant-isolation (workspace A không thấy data workspace B).
- [ ] Mọi write endpoint có idempotency key hoặc test xác nhận không tạo duplicate khi retry.

## 2e. Verify Execution & Planning (§4.4) đã đủ

**Task:** chạy integration test chuỗi `project → initiative → OKR cycle → 12-week plan → weekly plan` bằng handler hiện có, xác nhận không có lỗi liên kết. Không cần viết thêm entity mới ở bước này.

**Acceptance:**
- [ ] 1 integration test end-to-end pass cho chuỗi trên.

## Dependency

2a → 2b → 2c → 2d tuần tự (mỗi bước phụ thuộc bước trước). 2e độc lập, có thể làm song song bất kỳ lúc nào. Toàn bộ Phase 2 phụ thuộc Phase 1a (TenantContext) đã xong.
