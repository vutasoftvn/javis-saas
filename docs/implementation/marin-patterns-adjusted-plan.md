# Marin Patterns Integration — Plan điều chỉnh & triển khai chi tiết

**Ngày:** 2026-08-26
**Nguồn:** đối chiếu `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` với code thật (3 Explore agent độc lập cho registry/evals/runtime, 1 Plan agent cho thiết kế chi tiết, 1 lần verify lại phát hiện sai lệch về trạng thái runtime).
**Trạng thái:** PLAN — chưa thi công. Không phần nào trong tài liệu này đã code.

---

## Context

`COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` đề xuất COSA học các pattern kiến trúc từ dự án Marin (marin-community/marin): semantic identity tách khỏi execution context, `name@version` + fingerprint, typed artifact ref, provenance/lineage là domain state hạng nhất, offline deterministic DAG cho eval/build, cache theo fingerprint. Tài liệu **không** muốn đưa Marin/Fray/Iris/Levanter làm dependency runtime — chỉ học pattern kiến trúc.

Tài liệu được viết rất chi tiết (30 mục) nhưng chưa audit sâu code thật trước khi viết, nên có sai lệch cần điều chỉnh. Sau khi audit, phát hiện 3 điểm (2 điểm đầu vẫn đúng sau khi verify lại, điểm 3 đã bị đảo ngược so với kết luận audit ban đầu — xem ghi chú cuối mục):

1. **Registry/Artifact identity đã tồn tại, không phải khoảng trống.** `PinnedSkillRef` (`packages/agent_core/contracts/identity.py:41-51`) và đặc biệt `PinnedSpecIdentity` (`packages/agent_core/governance/contracts.py:10-19`: spec_kind/spec_id/spec_version/definition_hash) đã chính là mô hình `ArtifactRef` mà tài liệu muốn "tạo mới". `governance/hashing.py` đã có canonical SHA-256 hash (sort keys, order-independent) đúng §6.2 của tài liệu gốc. `registry/publisher.py` + `registry/repository.py` đã idempotent theo (kind, id, hash) và reject conflict đúng INV-A2. Nếu làm theo tài liệu gốc (tạo `ArtifactIdentity`/`ArtifactRef` dataclass song song), sẽ vi phạm CLAUDE.md rule 4 và chính §25.6 của tài liệu gốc ("không tạo persistence/type mới khi đã có ownership").

2. **Eval infra gần như trống**, ngược lại với ngôn ngữ "mở rộng" của tài liệu gốc. Không có `EvalSuite`/`EvalRun` Python model (chỉ có `EvalTestCase`, `EvalResult` rời rạc, không ref suite/run), không có `PromotionEvidence`/`PromotionDecision` (0 kết quả grep toàn repo), Skill Optimization Lab (`packages/agent_core/skills/lab/lab.py`) có ghi mutation chain nhưng không traceable sang eval evidence thật. Đây là greenfield build, không phải extend.

3. **Runtime production — ĐÃ ĐÓNG, KHÔNG còn mock.** Audit ban đầu (đọc `docs/implementation/production-runtime-closure.md`) kết luận nhầm runtime vẫn mock, vì trích dẫn đúng bảng "Đối chiếu" (mô tả trạng thái TRƯỚC khi fix) mà bỏ qua phần tóm tắt "Trạng thái triển khai" ở đầu file. Verify lại bằng code thật (2026-08-26): `apps/cosa/composition/agent_plane.py:19,302` import và dựng `RealOpenAIAgentsSDKKernel` làm mặc định; mock keyword-matching fallback đã bị xoá khỏi `packages/agent_core/kernel/openai_agents_kernel.py:461-474` (raise lỗi tường minh nếu thiếu `model_client`, không còn silent-mock). Git log xác nhận commit `3065a694 Phase 0-6 hoàn thành toàn bộ` đã nằm trên `main`. **Kết luận: không còn runtime blocker.** Phần còn thiếu thật là `apps/cosa/agents/specs.py` vẫn hard-code `AgentSpec` làm Python constant, chưa load qua registry, chưa set `definition_hash` — đây là gap về **registry-wiring**, có thể làm ngay trong Wave M2, không cần chờ plan nào khác.

Ba quyết định đã chốt với người dùng trước khi phát hiện điểm 3 bị đảo ngược (2 quyết định đầu vẫn giữ nguyên; quyết định về runtime-blocking được nới lỏng theo phát hiện mới):

- **Không tạo type hệ song song**: tổng quát hóa `PinnedSpecIdentity` đã có sẵn, không viết `ArtifactIdentity`/`ArtifactRef` dataclass mới cạnh nó.
- **Eval scope làm thật, đầy đủ**: xây `EvalSuite`/`EvalCase`/`EvalRun`/`EvalResult` + `PromotionEvidence` như evidence artifact thật trong `agent_core`, nhưng quyền quyết định promote (`PromotionDecision`, activation) thuộc `services/cosa` — `agent_core` chỉ tạo evidence, không tự quyết.
- **Runtime integration (đã cập nhật)**: KHÔNG còn cần đánh dấu BLOCKED. Wave M2 bao gồm cả việc wiring `apps/cosa/agents/specs.py` để load AgentSpec qua registry (exact version + fingerprint) thay vì hard-code, vì runtime thật đã sẵn sàng nhận spec đã resolve.

---

## Kiến trúc đích (đã điều chỉnh)

```
PinnedSpecIdentity (governance/contracts.py)   ← tổng quát hóa, KHÔNG tạo ArtifactRef mới
   kind: str (mở rộng từ Literal["agent","workflow"])
   id, version, definition_hash
        │
        ├── AgentSpec pin: prompt_ref, model_policy_ref, tool_contract_refs (MỚI — hiện là dict thô)
        ├── apps/cosa/agents/specs.py load qua registry thay vì hard-code (MỚI)
        ├── EvalSuite/EvalRun/EvalResult (MỚI — hiện gần như trống)
        └── PromotionEvidence (MỚI — evidence artifact, KHÔNG có quyền quyết định)
                │
                ▼
        services/cosa: PromotionDecision + activation (authority, ngoài scope plan này)
```

---

## Wave M0 — Audit & contract freeze (P0)

**Mục tiêu:** khóa quyết định generalization trước khi code, tránh vừa làm vừa đổi hướng.

**Task breakdown (theo thứ tự):**

1. Viết `docs/implementation/M0_AUDIT_AND_INVENTORY.md` — ma trận `concept | existing code | gap | action` dựa trên audit đã có (bảng đối chiếu ở mục Context).
2. Xác nhận `definition_hash()` (`packages/agent_core/governance/hashing.py`) đã canonical đúng §6.2 tài liệu gốc (sort keys, order-independent, loại trừ runtime context) — chỉ cần thêm prefix `sha256:` nếu output hiện tại chưa có.
3. Quyết định generalization cho `PinnedSpecIdentity`: mở rộng `spec_kind: Literal["agent","workflow"]` → `str`/enum mở rộng gồm `prompt`, `skill`, `eval_suite`, `model_policy`, `knowledge_snapshot`, `promotion_evidence`. Giữ tên class `PinnedSpecIdentity` (không rename trừ khi thấy thật sự cần khi code M1) — ghi quyết định thành `docs/architecture/adr/ADR-ARTIFACT-IDENTITY-001.md` (file mới, theo format ADR hiện có trong `docs/architecture/adr/`).
4. Viết golden fixture test cho fingerprint: `tests/agent_core/test_m0_fingerprint_fixtures.py` — key-order independence, runtime-context exclusion (run_id/region không đổi hash), dependency thay đổi → fingerprint đổi.

**File liên quan:** `packages/agent_core/governance/hashing.py` (đọc, không sửa), `packages/agent_core/governance/contracts.py` (đọc, quyết định trước khi sửa ở M1).

**Exit criteria:** ma trận audit không phát hiện module/bảng trùng ownership; test fixture pass với `definition_hash()` hiện tại; ADR generalization được ghi lại.

---

## Wave M1 — Generalize PinnedSpecIdentity (P0)

**Mục tiêu:** có một identity/fingerprint primitive dùng chung cho mọi domain, không tạo type thứ hai.

**Task breakdown:**

1. Sửa `packages/agent_core/governance/contracts.py`: mở rộng `PinnedSpecIdentity.spec_kind` theo quyết định M0-3.
2. Thêm dependency edge model tối giản trong cùng file hoặc `packages/agent_core/governance/lineage.py` (mới, chỉ nếu M0 xác nhận chưa có chỗ tương đương): `owner: PinnedSpecIdentity`, `dependency: PinnedSpecIdentity`, `relation: str`.
3. Thêm adapter method trên `PinnedSpecIdentity` để convert từ `PinnedSkillRef` (`packages/agent_core/contracts/identity.py`) — giữ backward compatibility, không sửa `PinnedSkillRef` nếu không cần.
4. Map lỗi vào `packages/agent_core/contracts/errors.py` hiện có (mismatch, missing dependency, drift) — chỉ thêm class mới nếu không có tương đương sau khi đọc file này.
5. Viết test: `tests/agent_core/test_m1_pinned_spec_identity.py` — dependency-drift propagation, version/hash conflict (`SpecVersionHashConflictError` đã có ở `registry/repository.py`), adapter lossless.

**File liên quan:** `packages/agent_core/governance/contracts.py`, `packages/agent_core/contracts/identity.py`, `packages/agent_core/contracts/errors.py`.

**Exit criteria:** `PinnedSpecIdentity` dùng được cho agent/skill/eval/knowledge domain mà không có type thứ hai cạnh tranh; test M1 pass.

---

## Wave M2 — Registry integration, dependency pinning & runtime wiring (P0/P1)

**Mục tiêu:** AgentSpec pin đầy đủ dependency bằng exact ref, và Run thật sự load spec qua registry thay vì hard-code.

**Task breakdown:**

1. Thêm `PromptSpec`, `ModelPolicySpec`, `ToolContractSpec` theo pattern `AgentSpec.compute_hash()` đã có ở `packages/agent_core/contracts/spec.py` — file mới `packages/agent_core/contracts/prompt.py`, `model_policy.py`, `tool_contract.py`. Hiện `model_policy` đang là `dict[str, Any]` thô (`contracts/spec.py:23`).
2. Mở rộng `AgentSpec` (`packages/agent_core/contracts/spec.py`) thêm `prompt_ref`, `model_policy_ref`, `tool_contract_refs` kiểu `PinnedSpecIdentity`, optional trong giai đoạn transition (không breaking existing callers).
3. Mở rộng `packages/agent_core/registry/publisher.py`: thêm `publish_prompt_spec()`, `publish_model_policy_spec()`; verify dependency tồn tại trong registry trước khi publish AgentSpec pin chúng.
4. Viết/hoàn thiện resolver "exact resolution" (kind+id+version+expected_fingerprint), tách khỏi "authoring resolution" (floating, chỉ cho UI/draft) theo §7.3 tài liệu gốc — `packages/agent_core/registry/resolver.py` (kiểm tra trước xem đã có file này chưa, nếu có thì extend).
5. **Wiring runtime (không còn blocked):** sửa `apps/cosa/agents/specs.py` để `COSA_FINANCE_AGENT_SPEC`/`COSA_OPERATIONS_AGENT_SPEC` được publish vào registry một lần (script/migration seed) thay vì define trực tiếp làm Python constant; sửa nơi dispatch (`apps/cosa/api/routes.py`, `apps/cosa/worker/handlers.py`) để resolve exact spec + fingerprint từ registry trước khi tạo `RunRecord`, thay vì import constant trực tiếp.
6. Cập nhật lineage: sau khi publish AgentSpec, ghi dependency edge (AgentSpec → Prompt/ModelPolicy/Skill/ToolContract) dùng model ở Wave M1.

**File liên quan:** `packages/agent_core/contracts/spec.py`, `packages/agent_core/registry/publisher.py`, `packages/agent_core/registry/resolver.py`, `apps/cosa/agents/specs.py`, `apps/cosa/api/routes.py`, `apps/cosa/worker/handlers.py`, `apps/cosa/composition/agent_plane.py` (chỉ đọc để hiểu nơi RunRecord được tạo).

**Test:** `tests/agent_core/test_m2_registry_integration.py` (publish/resolve prompt+model_policy, AgentSpec fingerprint đổi khi dependency đổi, resolver reject mismatch/missing) + test tích hợp ở `apps/cosa` (Run tạo từ spec resolve qua registry, không phải import trực tiếp constant).

**Exit criteria:** AgentSpec publish được với đầy đủ pinned refs (không floating); resolver reject fingerprint mismatch; một Run production thật sự resolve AgentSpec qua registry (verify bằng test qua process thật theo CLAUDE.md rule 6, không chỉ instance thứ hai trong cùng process).

---

## Wave M3 — Eval artifacts thật (P1)

**Mục tiêu:** EvalSuite/EvalRun/EvalResult trở thành reproducible evidence có version+fingerprint+lineage.

**Task breakdown:**

1. Xây `EvalCaseSet`, `EvalSuite`, `EvalRun`, `EvalResult` trong `packages/agent_core/evals/models.py` (hiện chỉ có `EvalTestCase`/`EvalResult` rời rạc, không ref suite/run) — có `to_artifact_ref()` dùng `PinnedSpecIdentity`, fingerprint theo §9.2 tài liệu gốc (case set + scorer version + threshold, loại trừ runtime context).
2. Viết `packages/agent_core/evals/repositories.py` (hiện không tồn tại) cho persistence các model trên.
3. Audit kỹ `agent_evals.*` migration hiện có trước khi ALTER — bảng `runs`/`results` đã có `target_version`/`target_definition_hash` nhưng thiếu suite fingerprint và case_set ref. Viết migration bổ sung cột (ưu tiên ALTER, không tạo bảng mới trừ khi cần bảng `case_sets` riêng vì bản chất immutable khác với `runs`).
4. Wire Skill Optimization Lab (`packages/agent_core/skills/lab/lab.py`, `packages/agent_core/skills/lab/models.py`): thêm `eval_run_id` vào `SkillCandidateRecord`/`SkillMutationRecord` để lineage skill→candidate→eval evidence traceable thật.

**File liên quan:** `packages/agent_core/evals/models.py`, `packages/agent_core/evals/repositories.py` (mới), `packages/agent_core/evals/runner.py`, `packages/agent_core/migrations/008_agent_evals.sql` (đọc trước khi viết migration mới nối tiếp), `packages/agent_core/skills/lab/lab.py`, `packages/agent_core/skills/lab/models.py`.

**Test:** `tests/agent_core/test_m3_eval_artifacts.py` — hai `EvalRun` cùng target+suite nhưng khác execution context không tạo hai suite identity khác nhau; suite fingerprint đổi khi case set/scorer version đổi; Skill Lab mutation record trace được sang eval evidence thật.

**Exit criteria:** như trên, tất cả test pass qua migration + repository thật (không mock DB).

---

## Wave M4 — Promotion evidence (P1, KHÔNG chứa promotion authority)

**Mục tiêu:** promotion không còn dựa vào "test pass mơ hồ"; evidence có thể stale-detect.

**Task breakdown:**

1. Xây `PromotionEvidence` (evidence_id, target ref, required eval_run_ids, observed_fingerprints, policy_version, policy_checks_passed) trong `packages/agent_core/evals/promotion.py` (mới) — immutable, có `is_stale()`.
2. Xây `PromotionGate` logic (`packages/agent_core/evals/promotion_gate.py`, mới) — check stale/dependency drift/failed eval, output `PromotionGateResult`, không tự activate gì.
3. Viết migration cho `agent_evals.promotion_evidence` (đọc schema M3 trước để tái dùng cột nếu hợp lý).
4. Viết `docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md` — contract ranh giới: `agent_core` export read-only evidence-query API; `services/cosa` sở hữu `PromotionDecision` + activation, đúng CLAUDE.md 4 vùng kiến trúc và §12.3 tài liệu gốc. Không code phía `services/cosa` trong wave này trừ khi user yêu cầu — chỉ document contract.

**File liên quan:** `packages/agent_core/evals/promotion.py` (mới), `packages/agent_core/evals/promotion_gate.py` (mới), migration mới nối tiếp M3.

**Test:** `tests/agent_core/test_m4_promotion_evidence.py` — evidence stale detection khi fingerprint drift sau eval pass; gate reject khi dependency drift/missing/eval fail.

**Exit criteria:** promotion bị block khi evidence stale; không có code nào trong `agent_core` tự set trạng thái production.

---

## Wave M5 — Offline DAG (P2, optional)

**Mục tiêu:** tăng tốc eval/build pipeline mà không viết scheduler thứ hai.

**Task breakdown:**

1. Audit `packages/agent_core/workflows/engine.py` (đã có DAG, parallel step, checkpoint/resume, compensation) — xác nhận đủ dùng làm offline eval/build DAG chưa. Ghi kết quả vào `docs/implementation/M5_OFFLINE_DAG_AUDIT.md` trước khi code bất cứ gì.
2. Chỉ nếu audit xác nhận thiếu năng lực: viết `OfflineStep` adapter (`packages/agent_core/workflows/offline_steps.py`) + artifact-aware cache key (fingerprint + dependency fingerprints, `packages/agent_core/workflows/artifact_cache.py`).

**Exit criteria:** quyết định reuse-vs-build ghi thành audit note trước khi viết code; nếu build, chỉ là adapter mỏng.

---

## Không làm trong plan này

- Không tạo `ArtifactIdentity`/`ArtifactRef` dataclass mới song song `PinnedSpecIdentity`.
- Không xây `PromotionDecision`/activation trong `agent_core` — thuộc `services/cosa`.
- Không đưa Marin/Fray/Iris/Levanter vào làm dependency.
- Không viết code cho phía `services/cosa` promotion authority trong Wave M4 — chỉ document contract ranh giới.

---

## Verification

- Mỗi wave có test suite riêng trong `tests/agent_core/` (unit cho fingerprint/dependency-drift/conflict, integration cho publish→lineage→resolve, và cho Skill Lab→eval lineage, và cho Run thật resolve spec qua registry ở M2).
- Golden fixture test cho canonical fingerprint (key-order independence, runtime-context exclusion) chạy trong CI, không cho phép đổi ngầm khi refactor serializer (versioned `fingerprint_schema_version` nếu phải đổi thuật toán).
- Trước khi báo "Wave X xong": chạy test thật (không chỉ code tồn tại), đối chiếu CLAUDE.md rule 11 (không tuyên bố xong khi chưa test) và rule 6 (durability test phải qua process thật nếu có claim restart-safe) — đặc biệt cho Wave M2 phần Run resolve spec qua registry.
- Trước khi dùng lại bất kỳ kết luận nào về "runtime đang mock" từ tài liệu/memory cũ: verify lại bằng `grep -n "RealOpenAIAgentsSDKKernel" apps/cosa/composition/agent_plane.py` — bài học từ chính plan này (xem Context điểm 3).
