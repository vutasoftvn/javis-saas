# Hướng dẫn: Thêm skill mới

## Khi nào cần

Khi có 1 khối instruction/technique tái sử dụng được giữa nhiều agent (vd "cách viết báo cáo cạnh tranh", "cách phân tích dependency"), KHÔNG khi chỉ cần thêm 1 dòng instruction riêng cho 1 agent cụ thể.

## Trước tiên: câu hỏi bắt buộc (CLAUDE.md #3)

Đây có phải Skill thật không, hay nên là Tool/Workflow/Knowledge/Executor/Integration? Skill = tri thức/kỹ thuật tái dùng, không phải side-effect (đó là Capability) và không phải 1 vai trò nghiệp vụ mới (đó là Agent).

## Vòng đời (Blueprint V2 §69.2, đã activate qua `ADR-SKILL-IDENTITY-trigger-based-evaluation.md`)

`Draft → Candidate → Evaluated → Published (immutable)`. Publish qua `packages/agent/registry/publisher.py::publish_skill_spec()` — ghi vào `agent_registry.published_specs` (composite PK `(spec_kind, spec_id, version)`, `spec_kind='skill'`), **immutable sau publish** — sửa nghĩa là publish version mới, không update tại chỗ.

## Các bước

1. Tạo source skillpack tại `skillpacks/<domain>/<skill-id>/{manifest.yaml,SKILL.md}`:
   - `manifest.yaml` chứa metadata (`metadata.id`, `metadata.version`, domain/category, `runtime.entrypoint: SKILL.md`, `runtime.tools`, permissions, risk, trust).
   - `SKILL.md` có YAML frontmatter với `name = normalize_discovery_name(metadata.id)` và `description`, theo sau là nội dung chỉ dẫn chuyên môn và mục `Allowed Tool Calls` (nếu có dùng tool).
2. Nếu skill cần eval trước khi publish (đề xuất mutation/optimization) → chạy qua Skill Optimization Lab (`packages/agent/skills/lab/`) — Executor→Scorer→Mutator→Challenger, **không bao giờ tự động publish**, luôn cần bước "keep/revert" tường minh.
3. Agent muốn dùng skill: thêm `PinnedSkillRef` (hash-pinned, `packages/agent/contracts/identity.py`) vào `AgentSpec.pinned_skills` — KHÔNG tham chiếu theo tên/version nổi (floating reference); `SkillResolver.resolve()` reject nếu hash mismatch.
4. `PromptBundle` (`packages/agent/prompts/bundle.py`) tự lắp `skill_instructions` vào system message khi kernel resolve skill trước khi tạo Run — không cần code gọi thủ công ở call site.
5. Viết `docs/features/skills.md` cập nhật (nếu skill là ví dụ đáng chú ý) hoặc thêm mô tả vào skill's `SKILL.md`.

## Không được làm

- Không publish skill version mới mà không chạy full regression (Skill Optimization Lab invariant).
- Không để agent tham chiếu skill "latest" không pin hash — vi phạm anti-floating-reference.
- Không tạo file `skill.yaml` hay lưu tại `packages/agent/skills/library/` (đã chuẩn hoá sang `skillpacks/<domain>/<skill-id>/{manifest.yaml,SKILL.md}`).

