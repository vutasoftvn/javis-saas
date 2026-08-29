# PART REG — Skill Registry HTTP backend + Flutter routing

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §3, §5
**Nhánh đề xuất:** `msmk/part-reg-skill-registry`
**Phụ thuộc:** PART 0

## Context

`frontend/lib/modules/skills/services/skill_registry_service.dart` gọi:
`POST /skills/sync-built-in`, `GET /skills`, `POST /skills/candidates`,
`POST /skills/:id/evaluate`, `POST /skills/:id/promote`, `POST /skills/:id/deprecate`,
`POST /skills/:id/feedback`. `frontend/lib/modules/skills/views/skill_registry_view.dart` hiển
thị vòng đời candidate → evaluation → active → deprecated.

**Không có backend** cho các route này: COSA FastAPI (`apps/cosa/api/routes.py`) chỉ có prefix
`/agent` (conversations, runs, approvals, connectors, schedules, knowledge); Encore services
không expose `/skills/*`. UI hiện chạy vào không khí.

Part REG dựng HTTP backend đặt đúng nguồn sự thật: `agent_registry.published_specs`
(`spec_kind="skill"`) qua `SpecRegistryRepository` + `SkillCandidate`
(`packages/agent/skills/contracts.py`). **`sync-built-in` là publish có kiểm, KHÔNG phải
auto-discovery runtime** — không được phá regression `tests/apps/cosa/test_agent_plane_skillpack_boundary.py`.

## Pattern tái dùng

- Router FastAPI + `get_cosa_plane(request)` + `get_authenticated_identity`:
  `apps/cosa/api/routes.py` (mẫu `@router.post("/approvals/{approval_id}/decision", ...)`).
- Publish immutable: `publish_skill_spec(spec, repository=spec_registry, publisher=...)`
  (`packages/agent/registry/publisher.py`) — idempotent nếu cùng hash, raise
  `SpecVersionHashConflictError` nếu version đã publish với nội dung khác.
- Resolve + hash-pin: `SkillResolver.resolve()` (`packages/agent/skills/resolver.py`).
- Contract skillpack + validator: `packages/agent/skills/skillpack_contract.py`
  (`validate_skillpack_tree`).
- `SkillSpec`/`SkillCandidate`/`SkillStatus`: `packages/agent/skills/contracts.py`.
- Flutter API client normalize: `frontend/lib/core/network/api_client.dart::normalizeEndpoint`.

## Danh sách file + thay đổi

### REG.1 Backend

| File | Thay đổi |
| --- | --- |
| `apps/cosa/api/skill_registry_routes.py` (mới) | `create_skill_registry_router() -> APIRouter(prefix="/agent/skills", tags=["skill-registry"])`. Endpoint: <br>• `GET ""` — list từ `plane.spec_registry` (`spec_kind="skill"`) + candidate store; filter query `domain`, `status`. Trả origin / adapted-from SHA (đọc từ `skill-source-attribution.md` hoặc `SkillSpec.references`) / version / `definition_hash` / `required_capabilities` / `eval_score` / runtime-state (pinned vào AgentSpec nào). <br>• `POST "/sync-built-in"` — chạy `validate_skillpack_tree(REPO_ROOT/"skillpacks")`; nếu 0 violation, build `SkillSpec` từ mỗi pack (`instructions` = body `SKILL.md`, `required_capabilities` từ `manifest.runtime.tools` đã lọc qua tập capability đăng ký, `references` = `{source_path, upstream}` từ `## Nguồn`), `publish_skill_spec()` mỗi cái (idempotent theo hash). Trả danh sách `{skill_id, version, definition_hash, published: bool}`. **Không** đăng ký capability, **không** đụng `cap_registry`. <br>• `POST "/candidates"` — tạo `SkillCandidate`. <br>• `POST "/{skill_id}/evaluate"` — chạy eval suite của pack, ghi `eval_score` vào candidate. <br>• `POST "/{skill_id}/promote"` — candidate → published; **bắt buộc** field `approved_by` + `approval_reason` (human approval); thiếu → `422`. <br>• `POST "/{skill_id}/deprecate"` — set `SkillStatus.RETIRED` (không xoá bản ghi). <br>• `POST "/{skill_id}/feedback"` — ghi feedback record. Tất cả: workspace-scoped từ `identity`, audit event qua `plane`. |
| `apps/cosa/api/app.py` | `app.include_router(create_skill_registry_router())` cạnh `app.include_router(router)` (dòng ~96). |
| `apps/cosa/api/schemas.py` | DTO: `SkillListItem`, `SyncBuiltInResponse`, `CreateCandidateRequest/Response`, `EvaluateResponse`, `PromoteRequest` (`approved_by`, `approval_reason`), `DeprecateRequest`, `FeedbackRequest`. |
| `packages/agent/skills/candidate_store.py` (mới nếu chưa có nơi lưu) | `InMemory`/`Postgres` store cho `SkillCandidate` + feedback (bảng `agent_skill_candidates`, `agent_skill_feedback`). Nếu đã có store trong `skills/lab/` thì reuse. |

### REG.2 Flutter routing

| File | Thay đổi |
| --- | --- |
| `frontend/lib/core/network/api_client.dart` | `normalizeEndpoint`: `/skills*` → `/agent/skills*` (hoặc sửa thẳng service). |
| `frontend/lib/modules/skills/services/skill_registry_service.dart` | 7 method trỏ `/agent/skills/*`; map status → typed result (`401/403` auth, `404` not found, `409` conflict, `422` missing-approval); bỏ `catch → return`. `promoteSkill` gửi `approvedBy` + `reason`. |
| `frontend/lib/modules/skills/views/skill_registry_view.dart` | Bind từ response thật: origin, adapted-from SHA, version, hash, `requiredCapabilities`, `evalResult`, runtime state (pinned/none). Bỏ dữ liệu placeholder. |

### REG.3 Test

| File (mới) | Ca kiểm |
| --- | --- |
| `tests/apps/cosa/test_skill_registry_routes.py` | `GET /agent/skills` list rỗng khi chưa sync; `POST /agent/skills/sync-built-in` → publish N pack, gọi lần 2 idempotent (không tạo version mới); `GET` sau sync trả đủ field; `POST /agent/skills/{id}/promote` thiếu `approved_by` → 422; có → status `published`; `deprecate` → `RETIRED`, bản ghi vẫn còn; workspace isolation (identity workspace A không thấy candidate workspace B); sau `sync-built-in`, `SkillResolver.resolve(PinnedSkillRef(id, version, hash))` OK, hash sai → `SKILL_RESOLUTION_ERROR`. |
| `tests/apps/cosa/test_agent_plane_skillpack_boundary.py` | Giữ nguyên — chạy lại để chứng minh Part REG **không** thêm capability, **không** thêm loader vào `build_cosa_agent_plane()`. |
| `frontend/test/skill_registry_service_test.dart` | Route/DTO/error state mới. |

## Verify

```text
python -m pytest tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_agent_plane_skillpack_boundary.py -q
cd frontend && flutter analyze && flutter test test/skill_registry_service_test.dart
# gọi thử: uvicorn apps.cosa.api.app:app → POST /agent/skills/sync-built-in → GET /agent/skills
```

## Definition of Done

- [ ] Router `/agent/skills/*` (7 endpoint) gắn vào `apps/cosa/api/app.py`, workspace-scoped, audit event.
- [ ] `sync-built-in` chạy `validate_skillpack_tree` trước, publish immutable qua `publish_skill_spec()`, idempotent theo hash; **không** đụng `cap_registry`.
- [ ] `promote` bắt buộc human approval (`approved_by` + `reason`); thiếu → 422.
- [ ] `deprecate` set `RETIRED`, không xoá.
- [ ] Flutter Skill Registry gọi `/agent/skills/*`, hiển thị origin/SHA/version/hash/capabilities/eval/runtime-state từ response thật, phân biệt được lỗi.
- [ ] `test_skill_registry_routes.py` xanh; `test_agent_plane_skillpack_boundary.py` vẫn xanh (5 capability, không loader).
- [ ] `flutter analyze/test` xanh.
