# Phase 10 — P2 Hardening/Scale (Trigger-Based, + ADR-SKILL-IDENTITY, Plugin Trust, Advanced LangGraph)

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 10". Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3, §4.

## Mục tiêu

Không prebuild — chỉ trigger từng mục khi có nhu cầu sản phẩm cụ thể, tránh over-engineering. Áp dụng nguyên vẹn cho cả mục gốc lẫn mục Hermes/LangGraph bổ sung.

## Điều kiện tiên quyết

Phase 9 xong; và với TỪNG mục dưới đây, phải có lý do cụ thể (feature request, incident, scale limit thật) trước khi bắt đầu — không làm "vì roadmap nói vậy".

## Danh sách (gốc) — mỗi mục là 1 quyết định độc lập, không phải trình tự bắt buộc

1. L3 Capability Implementation Identity (ADR-A, hiện DEFERRED) — chỉ pin handler/schema/connector implementation version nếu có case cụ thể cần rollback an toàn.
2. Multi-worker execution leases — chỉ khi có distributed workers thật.
3. Work queue/coalescing scheduler — chỉ khi sản phẩm cần recurring/background work thật.
4. Plugin/extensibility framework — chỉ khi có use case cụ thể cần third-party/community extension.
5. Role hierarchy/quorum policy mở rộng — chỉ khi `AllOf`/`AnyOf`/`Quorum` hiện có không đủ biểu diễn nhu cầu approval thật.
6. Dormant Run TTL/expiry UX (ADR-D) — chỉ khi có Run thật tồn đọng lâu cần chính sách rõ ràng.
7. Multi-region/cloud artifact distribution — chỉ khi cần thật.

## Bổ sung Hermes/LangGraph — mục mới, cùng nguyên tắc trigger-based

8. **ADR-SKILL-IDENTITY** — trigger: có use case sản phẩm thật đầu tiên cần một Skill tham gia execution (không riêng delegation — bất kỳ Run nào cần resolve Skill reference). Quyết định 1 trong 3 cơ chế:
   ```text
   A. AgentSpec reference exact SkillSpec version/hash
   B. Skill contents compiled trực tiếp vào AgentSpec definition_hash
   C. Skill trở thành một spec_kind mới trong PinnedSpecIdentity (mở rộng spec_kind = agent | workflow | skill)
   ```
   Không preselect phương án C ngay — đánh giá cả 3 khi trigger xảy ra. Cho tới khi ADR này chốt, `skill_refs` trong AgentSpec (placeholder từ Phase 1) vẫn giữ rỗng/không execution-affecting (đã enforce từ Phase 9 Track 9D).
9. **Plugin trust/quarantine lifecycle** — trigger: plugin installation trở thành requirement sản phẩm thật.
   ```text
   DISCOVERED → QUARANTINED → SCANNED → VERIFIED → INSTALLED → TENANT_ENABLED → ACTIVE
   (terminal/administrative: REJECTED, DISABLED, REVOKED)
   ```
   Metadata cần có: identity, version, hash, publisher, source, declared capabilities, required permissions, connector requirements, scan result, installation provenance, trust/signing metadata. Plugin không được bypass Capability Gateway, Governance, Run tool-call ledger dưới bất kỳ hình thức nào.
10. **Rich delegation steer/stop UX** — trigger: DelegationEnvelope (Phase 9 Track 9B) đã chạy production, và có nhu cầu thật cho operator can thiệp giữa chừng (không chỉ status/cancel cơ bản đã có ở Phase 9). Mở rộng vocabulary sự kiện nếu cần (`delegation.paused`, `delegation.resumed`,...), vẫn phải durable — control event đi qua child Run input/control channel, không mutate in-memory object.
11. **Advanced LangGraph features** — chỉ trigger nếu Phase 6 đã Adopt VÀ có use case thật:
    - Subgraph-as-child-Run: mỗi LangGraph subgraph namespace cần một pinned WorkflowSpec riêng + auditable subexecution identity — namespace LangGraph một mình KHÔNG đủ làm business audit identity.
    - Time-travel/fork: expose qua Run Fork API auditable (`parent_run_id`, `fork_checkpoint_ref`) — không bao giờ pretend side effect đã commit trước khi fork "chưa từng xảy ra".

## Definition of Done — Phase 10

Không áp dụng theo nghĩa "hoàn thành toàn bộ" — mỗi mục (cả gốc lẫn bổ sung) có DoD riêng khi được trigger, viết bổ sung vào chính file này tại thời điểm đó (ghi rõ lý do trigger + ADR liên quan).

## Rủi ro/lưu ý

**Gốc + bổ sung:** Rủi ro chính của cả phase là bị áp lực "làm cho đủ roadmap" — kỷ luật trigger-based phải giữ nghiêm, đặc biệt với mục 8 (ADR-SKILL-IDENTITY) vì đây là điểm supplement gốc từng để mơ hồ (chỉ trigger khi child inherit) — Integration Plan đã mở rộng phạm vi trigger, nhưng KHÔNG mở rộng thời điểm bắt buộc làm; vẫn chỉ làm khi có use case thật, không phải "vì phạm vi trigger đã rộng hơn nên nên làm sớm hơn".
