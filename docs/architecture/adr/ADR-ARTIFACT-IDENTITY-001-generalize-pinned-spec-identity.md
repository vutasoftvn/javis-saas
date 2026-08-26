# ADR-ARTIFACT-IDENTITY-001: Tổng quát hóa PinnedSpecIdentity thay vì tạo ArtifactIdentity/ArtifactRef mới

- **Trạng thái:** ACCEPTED (quyết định người dùng, phiên brainstorming đối chiếu `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` với code thật, 2026-08-26)
- **Ngày quyết định:** 2026-08-26
- **Tham chiếu:**
  - `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` (tài liệu gốc đề xuất `ArtifactIdentity`/`ArtifactRef`)
  - `docs/implementation/marin-patterns-adjusted-plan.md` (plan điều chỉnh, Wave M0/M1)
  - `packages/agent_core/governance/contracts.py::PinnedSpecIdentity`

---

## 1. Bối cảnh

Tài liệu Marin Patterns đề xuất tạo `ArtifactIdentity`/`ArtifactRef` (kind, name, version, fingerprint) làm primitive định danh chung cho mọi artifact (AgentSpec, PromptSpec, SkillSpec, EvalSuite, KnowledgeSnapshot, PromotionEvidence). Audit code thật (2026-08-26) phát hiện `packages/agent_core/governance/contracts.py::PinnedSpecIdentity` đã là đúng hình dạng đó: `spec_kind`, `spec_id`, `spec_version`, `definition_hash` — dùng canonical SHA-256 hash (`governance/hashing.py::definition_hash()`, sort_keys, order-independent). Tạo type mới song song sẽ vi phạm CLAUDE.md rule 4 ("Không nhân bản kiến trúc") và chính §25.6 của tài liệu gốc ("không tạo persistence mới khi hiện tại đã có ownership").

Giới hạn thật duy nhất: `PinnedSpecIdentity.spec_kind` hiện là `Literal["agent", "workflow"]`, hẹp hơn field cùng tên ở `registry/models.py::PublishedSpecRecord.spec_kind` (đã là `str` tự do, hỗ trợ `"skill"` qua `publish_skill_spec()`). DB constraint `agent_core_governance.spec_resolution_manifest_entries` cũng có `CHECK (spec_kind IN ('agent', 'workflow'))`.

## 2. Quyết định

1. **Không tạo `ArtifactIdentity`/`ArtifactRef`.** Dùng `PinnedSpecIdentity` làm identity primitive chung cho agent/skill/prompt/model_policy/tool_contract — domain nào cần resolve exact version+fingerprint vào một Run (qua `SpecResolutionManifest`) đều dùng type này.
2. Mở rộng `PinnedSpecIdentity.spec_kind` từ `Literal["agent", "workflow"]` thành `Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract"]` — enum tường minh (không dùng `str` tự do) để giữ an toàn kiểu, khác với `PublishedSpecRecord.spec_kind` (registry layer, không cần strict vì đã có DB UNIQUE constraint bảo vệ).
3. Mở rộng CHECK constraint tương ứng trên `agent_core_governance.spec_resolution_manifest_entries` bằng migration MỚI (không sửa `002_governance_temporal_model.sql` — migration đã apply là bất biến).
4. `EvalSuite`/`EvalRun`/`PromotionEvidence` (Wave M3/M4, chưa code) sẽ tham chiếu artifact khác qua field kiểu `PinnedSpecIdentity` nhúng trực tiếp trong bản ghi eval/promotion — KHÔNG đi qua `SpecResolutionManifest`/`agent_core_governance.spec_resolution_manifest_entries` (bảng đó chỉ dành cho identity mà một *Run* đã resolve, không phải cho offline eval/promotion artifact). Vì vậy `spec_kind` cho `"eval_suite"`/`"knowledge_snapshot"`/`"promotion_evidence"` KHÔNG cần thêm vào Literal này ở M1 — chỉ thêm khi một use case thật sự cần ghi entry đó vào manifest của một Run.
5. Thêm `SpecDependencyEdge` (owner/dependency/relation) làm lineage edge tối giản, tái dùng `PinnedSpecIdentity` cho cả hai đầu — không tạo `ArtifactDependency` type riêng.

## 3. Hệ quả

- `AgentSpec` (Wave M2, chưa code) sẽ thêm `prompt_ref`/`model_policy_ref`/`tool_contract_refs` kiểu `PinnedSpecIdentity` — không cần type mới.
- `PinnedSkillRef` (`contracts/identity.py`) giữ nguyên làm type ổn định cho `AgentSpec.pinned_skills` (đã có consumer thật, không refactor); thêm adapter `to_pinned_identity()` để dùng thống nhất trong lineage edge khi cần.
- Nếu về sau phát hiện một domain thật sự không tái dùng được `PinnedSpecIdentity` (ví dụ cần thêm field chỉ có ý nghĩa với domain đó), phải mở ADR mới ghi rõ lý do kỹ thuật — không tự ý tạo type song song.
