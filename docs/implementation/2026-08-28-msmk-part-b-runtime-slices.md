# PART B — Runtime slices (B1 / B2 / B3)

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §5
**Nhánh đề xuất:** `msmk/part-b1-context-copy`, `msmk/part-b2-research-brief`, `msmk/part-b3-competitive-intel`
**Phụ thuộc:** PART 0 + PART A-A + PART CTX + PART REG · **gate toàn cục**: `make tenancy-check` xanh + remediation PART 1 merge

## Context

Sau khi 8 pack Nhóm A đã adapt (Part A-A), CTX API canonical đã lên (Part CTX), Skill Registry
backend đã có (Part REG), và tenancy gate xanh, mới kích hoạt skill vào runtime theo
capability-first (`docs/features/skills.md §17-18`, hardening design §5). Mỗi slice là một
vertical slice rủi ro tăng dần: B1 chỉ tạo artifact → B2 đọc web read-only → B3 curated knowledge.

**Gate bắt buộc trước production cho mỗi slice** (theo program §5): eval 4 path; tenancy
isolation (cross-workspace deny); approval bind + resume; **restart recovery E2E qua durable
worker thật** (không instance thứ hai cùng process — CLAUDE.md #6); provider sandbox.

## Pattern tái dùng

- Capability read SPEC + handler: `apps/cosa/capabilities/operations_read.py`.
- Publish + pin: `publish_skill_spec()` → `PinnedSkillRef(skill_id, version, definition_hash)`
  vào `AgentSpec.pinned_skills` (`apps/cosa/agents/specs.py`, `COSA_OPERATIONS_AGENT_SPEC` mẫu).
- Resolve: `SkillResolver.resolve()` — hash lệch → `AgentRuntimeError(SKILL_RESOLUTION_ERROR)` trước khi tạo run.
- Artifact: `WorkspaceArtifact` kind `report`, `input_artifact_ids` cho lineage.
- Approval bind/resume: `create_approval_request(run_id, tool_call_id, checkpoint_ref)` +
  `verify_and_prepare_resume()` (`packages/agent_core/capabilities/approval_service.py`).
- Durable worker: `packages/agent_core/coordination/scheduler.py`, `runs/leases.py`; E2E qua
  `apps/desktop_worker` hoặc worker process thật.
- Knowledge ingestion: `apps/cosa/knowledge_ingestion/handler.py`, review route
  `apps/cosa/api/routes.py:1088`, `authority_class` + `ingest_status`.
- Recipe: `packages/agent_recipes/*/recipe.yaml` (`requires.skills[].ref`).

---

## PART B1 — Context & copy drafting (artifact-only, rủi ro thấp)

### Thay đổi

| File | Nội dung |
| --- | --- |
| `apps/cosa/capabilities/marketing_read.py` (mới) | `MARKETING_CONTEXT_READ_SPEC = CapabilitySpec(id="commercial.marketing_context.read", risk=CapabilityRisk.LOW, approval_policy=NEVER, input_schema={workspace_id}, output_schema={context})`. `create_marketing_context_read_handler(client)` → GET `/commercial/marketing-context` (Part CTX) với `X-Workspace-Id` từ `ctx`. Read-only. |
| `apps/cosa/composition/agent_plane.py` | `cap_registry.register(MARKETING_CONTEXT_READ_SPEC, create_marketing_context_read_handler(client))`. |
| `apps/cosa/agents/specs.py` | `COSA_MARKETING_AGENT_SPEC` (mới) hoặc mở rộng spec sẵn có: `pinned_skills = [PinnedSkillRef(marketing.positioning ...), PinnedSkillRef(marketing.copywriting ...)]` — version + hash lấy từ `publish_skill_spec()` (chạy qua Part REG `sync-built-in`). `required_capabilities` của 2 skill = `["commercial.marketing_context.read"]` (không write). |
| Frontend | Context tab (Part CTX) hiển thị draft/review state của artifact; Skill Registry (Part REG) hiển thị source/version/hash/required-capabilities/eval/runtime-state của 2 skill đã pin. |

### Hành vi
- Agent đọc product context đã authorized. Context trống → trả **draft + missing-evidence list**,
  không bịa số liệu/testimonial.
- Output: `WorkspaceArtifact` kind `report`, `input_artifact_ids` trỏ evidence (nếu có).
- Không capability network / business-write nào được cấp.

### Test (gate)
- `tests/agent_core/registry/test_skill_resolution.py` — valid pin / missing / hash mismatch cho 2 skill.
- `tests/apps/cosa/test_agent_plane_marketing_read.py` — `build_cosa_agent_plane()` expose
  `commercial.marketing_context.read`; cross-workspace → deny.
- Eval `tests/agent_core/skills/eval/test_marketing_positioning_eval.py` — 4 path (happy /
  context-trống→missing-evidence / stale context / prompt-injection trong context text).
- **Restart recovery E2E**: chạy slice qua durable worker, kill process giữa chừng, worker khác
  nhặt lease, run hoàn tất đúng 1 artifact (không nhân đôi).

### DoD B1
- [ ] 2 skill publish + pin (version + hash) vào `COSA_MARKETING_AGENT_SPEC`.
- [ ] `commercial.marketing_context.read` đăng ký tường minh + integration test.
- [ ] Context trống → artifact nêu missing-evidence, không bịa.
- [ ] Workspace khác không đọc được artifact/context.
- [ ] Eval 4 path + restart-recovery E2E + tenancy isolation xanh.
- [ ] `test_agent_plane_skillpack_boundary.py` count = 7 (5 + web.search + marketing_context.read), xanh.

---

## PART B2 — Research brief (read-only external)

**Phụ thuộc thêm:** PART SEARCH.

### Thay đổi

| File | Nội dung |
| --- | --- |
| `apps/cosa/agents/specs.py` | Pin thêm `PinnedSkillRef(marketing.market-research ...)` + `PinnedSkillRef(research.deep-research ...)`; `required_capabilities = ["web.search"]`. |
| `apps/cosa/capabilities/` | (dùng `web.search` từ Part SEARCH — không thêm mới) |
| `apps/cosa/` slice handler | Research output → `WorkspaceArtifact` kind `report` + candidate evidence (`trust=unreviewed`); **không** tự cập nhật `marketing_contexts` đã `approved`. |
| Frontend | Màn brief: claim / citation / confidence / contradiction + nút "đề xuất cập nhật context" → chỉ user review mới tạo write (PATCH CTX). |

### Test (gate)
- Eval: happy + stale/contradictory source + prompt-injection text từ web (kết quả search chứa
  "ignore previous instructions…" → agent không tuân).
- `web.search` capability test: denied allowlist domain; `QUOTA_EXCEEDED`.
- Artifact có citation cho mọi claim; không auto-promote sang context.
- Provider sandbox: Tavily fixture, không gọi mạng thật trong CI.

### DoD B2
- [ ] 2 skill research pin với `required_capabilities=["web.search"]`.
- [ ] Insight mới mặc định `trust=unreviewed`; context `approved` không đổi tự động.
- [ ] Prompt-injection từ web không đổi hành vi agent (eval chứng minh).
- [ ] Quota/allowlist enforce; provider sandbox test xanh.

---

## PART B3 — Curated knowledge & competitive intelligence

**Phụ thuộc thêm:** PART B2.

### Thay đổi

| File | Nội dung |
| --- | --- |
| `apps/cosa/knowledge_ingestion/` | Nối output research (Part B2) vào governed pipeline hiện có (flag `knowledge_ingestion_enabled()`); giữ `trust`/`sensitivity`/provenance theo `docs/features/marketing-evidence-taxonomy.md` + map `authority_class` (research external → `EXTERNAL`). |
| `apps/cosa/capabilities/knowledge_read.py` (mới hoặc mở rộng) | Capability read profile/summary đã kiểm workspace + sensitivity. Profile **không bao giờ** đưa instruction từ website vào prompt như instruction đáng tin (sanitize + nhãn untrusted). |
| `apps/cosa/agents/specs.py` | Pin `PinnedSkillRef(strategy.competitor-profiling ...)`. |
| `packages/agent_recipes/sales/competitor-intelligence/recipe.yaml`, `packages/agent_recipes/research/research-synthesize/recipe.yaml` | Đổi `requires.skills[].ref` từ floating `skillpacks/strategy/evidence-synthesis` sang tham chiếu pinned (`{skill_id, version, definition_hash}`). |
| Recipe loader | `packages/agent_recipes/` loader: parse `PinnedSkillRef` thay vì path; reject path string (floating ref). |

### Test (gate)
- Retrieval trả đúng sensitivity scope (workspace A không thấy `confidential` của B).
- Prompt-injection trong profile/website content không đổi hành vi.
- Recipe resolve qua pinned ref; floating `ref: skillpacks/...` → loader reject.
- Restart recovery E2E cho workflow competitive-intelligence qua durable worker.

### DoD B3
- [ ] Output research chảy vào knowledge-ingestion với trust/sensitivity/provenance đúng taxonomy.
- [ ] Profile/summary expose qua capability read đã kiểm workspace+sensitivity; nội dung web gắn nhãn untrusted.
- [ ] `strategy.competitor-profiling` pinned; 2 recipe dùng `PinnedSkillRef`, floating ref bị reject.
- [ ] Eval prompt-injection + sensitivity-scope + restart-recovery xanh.

---

## Verify (toàn Part B)

```text
make tenancy-check
python -m pytest tests/agent_core/registry/test_skill_resolution.py tests/apps/cosa -q
python -m pytest tests/agent_core/skills/eval -q
# restart recovery: chạy slice qua apps/desktop_worker thật, kill -9 giữa chừng, xác nhận 1 artifact duy nhất
```
