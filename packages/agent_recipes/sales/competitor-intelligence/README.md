# Recipe: Competitor Intelligence

Pattern: `research-synthesize` (Blueprint V2 §70).

## Trạng thái phụ thuộc (2026-08-24)

- `web.search` capability: **CHƯA implement** trong `apps/cosa/capabilities/` — recipe này khai báo yêu cầu, không giả định đã có sẵn. Cần đăng ký `CapabilitySpec` + handler thật trước khi recipe này chạy được end-to-end.
- Skill tham chiếu `skillpacks/strategy/evidence-synthesis`: **đã tồn tại** (`skillpacks/strategy/evidence-synthesis/`).

## Cách instantiate

Recipe này KHÔNG có authority riêng (theo `packages/agent_recipes/README.md`) — instantiate bằng cách:
1. Publish `web.search` (nếu chưa có) vào `CapabilityRegistry` qua composition root (`apps/cosa/composition/agent_plane.py`).
2. Tạo `AgentSpec` với `capability_refs=["web.search"]`, `pinned_skills` trỏ tới skill `evidence-synthesis` đã publish qua `publish_skill_spec()` (Wave 5, `packages/agent_core/registry/publisher.py`).
3. Chạy qua `ExecutionKernel.run()` như bất kỳ Run nào khác — không có execution path riêng cho recipe.
