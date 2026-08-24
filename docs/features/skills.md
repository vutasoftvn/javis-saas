# Skills

## 1. Mục đích

Skill = "how to perform" instruction/recipe bất biến theo version, resolve vào prompt qua `AgentSpec.pinned_skills`. Skill ≠ Tool ≠ Workflow ≠ Agent.

## 2. Khi nào sử dụng

Khi 1 agent cần chỉ dẫn chuyên môn tái sử dụng được, publish 1 lần và pin chính xác version+hash cho từng AgentSpec dùng nó.

## 3. Không dùng cho việc gì

Không dùng skill để mang business logic có side effect — đó là capability.

## 4. Kiến trúc và luồng dữ liệu

**Kích hoạt quan trọng (2026-08-24):** `ADR-SKILL-IDENTITY-trigger-based-evaluation.md` từng ở trạng thái "PENDING TRIGGER" — khoá skill khỏi runtime execution để tránh floating reference. Đã kích hoạt (§4 của ADR đó) khi Skill Optimization Lab (Blueprint V2) cần đúng khả năng này, chọn **Phương án A**: `AgentSpec.pinned_skills: list[PinnedSkillRef]`.

```
AgentSpec.pinned_skills = [PinnedSkillRef(skill_id, version, definition_hash)]
  → kernel.run(): SkillResolver.resolve(pinned_skills)
    → SpecRegistryRepository.get("skill", skill_id, version)
    → verify definition_hash khớp TUYỆT ĐỐI — mismatch/missing → AgentRuntimeError(SKILL_RESOLUTION_ERROR), raise TRƯỚC khi tạo RunRecord
  → skill.instructions inject vào PromptBundle (section riêng, giữa agent_instructions và locale_policy)
```

`publish_skill_spec()` dùng CHUNG registry với AgentSpec (`agent_registry.published_specs`, `spec_kind="skill"`) — không tạo bảng riêng cho skill.

3 tầng skill infra riêng biệt, không trùng nhau:
1. `skillpacks/<domain>/<skill-id>/{manifest.yaml,SKILL.md}` — file-based, dùng cho nội dung skill có sẵn (okr, marketing, strategy...).
2. `packages/agent_core/skills/{contracts,registry}.py` — `SkillSpec`/`SkillRegistry` in-memory, L0/L1 progressive disclosure index.
3. `agent_registry.published_specs` (spec_kind="skill") — durable publish path cho runtime resolution.

## 5. Public contracts/API

`agent_core.contracts.identity.PinnedSkillRef`, `agent_core.skills.resolver.SkillResolver`, `agent_core.registry.publisher.publish_skill_spec()`, `agent_core.skills.contracts.SkillSpec/SkillStatus/SkillCandidate`.

## 6. Database/schema liên quan

`agent_registry.published_specs` (migration 007, `spec_kind="skill"`).

## 7. Cấu hình

Không có config riêng — dùng `SpecRegistryRepository` đã cấu hình cho kernel.

## 8. Ví dụ sử dụng

```python
published = await publish_skill_spec(skill_spec, repository=spec_registry, publisher="tester")
agent_spec = base_spec.model_copy(update={"pinned_skills": [
    PinnedSkillRef(skill_id=published.spec_id, version=published.version, definition_hash=published.definition_hash)
]})
```

## 9. Cách bổ sung implementation mới

Publish `SkillSpec` mới qua `publish_skill_spec()`, pin vào `AgentSpec.pinned_skills`. Không sửa version đã publish — bump version.

## 10. Security/governance

`SkillResolver` từ chối resolve nếu hash không khớp — chống floating reference (agent chạy với skill content không xác định).

## 11. Error handling

`AgentRuntimeError(SKILL_RESOLUTION_ERROR)` — raise TRƯỚC khi tạo RunRecord (cùng nguyên tắc như spec publish conflict), tránh Run kẹt RUNNING.

## 12. Observability

Không có event riêng — lỗi resolve propagate raw (không phải RunResult FAILED).

## 13. Testing

`tests/agent_core/registry/test_skill_resolution.py`.

## 14. Migration/backward compatibility

`AgentSpec.pinned_skills` field mới, default `[]` — không breaking change cho spec cũ.

## 15. Troubleshooting

`SKILL_RESOLUTION_ERROR` khi resolve: kiểm tra `definition_hash` trong `PinnedSkillRef` có khớp CHÍNH XÁC với `publish_skill_spec()` trả về không (không dùng hash tự tính lại thủ công).

## 16. Definition of Done

- [x] Contract, resolver, wiring cả 2 kernel, test đầy đủ (missing/mismatch/happy path)
- [ ] `skillpacks/` manifest.yaml chưa bổ sung field liên kết tới registry (để lại có chủ đích, chưa có consumer đọc field đó)
