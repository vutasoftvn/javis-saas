# Data Model — Sơ đồ schema Postgres (sau Wave 0-11)

Xem `docs/architecture/adr/ADR-DATABASE-SCHEMA-OWNERSHIP.md` cho bảng sở hữu đầy đủ. Tóm tắt quan hệ chính:

```text
agent_core.runs (run_id PK)
  ├── agent_core.run_checkpoints (run_id, sequence_no)
  ├── agent_core.run_events (run_id, sequence_no — append-only)
  ├── agent_core.run_tool_calls (run_id, tool_call_id — PK composite)
  │     └── agent_core.approvals (run_id, tool_call_id — FK composite, decision_version CAS)
  └── agent_core.idempotency_claims (scope_kind, scope_key, capability_id, idempotency_key — UNIQUE)

agent_core_governance.invocation_governance_state (run_id, tool_call_id — PK composite)
  └── agent_core_governance.invocation_governance_history (append-only, có `source`)

agent_conversation.conversations (conversation_id PK)
  └── agent_conversation.messages (conversation_id, sequence_no)
        └── agent_conversation.message_attachments (message_id FK)

agent_registry.published_specs (spec_kind, spec_id, version — PK composite)
  # spec_kind ∈ {"agent", "skill"} — DÙNG CHUNG, không tách bảng riêng cho skill

agent_evals.suites → cases → runs → results (SQL tồn tại, CHƯA có Python repository)
agent_evals.skill_candidates → skill_mutations (SQL tồn tại, CHƯA có Python repository — Lab dùng in-memory)

agent_memory.agent_memories (id PK, scope_type/scope_id generic, status lifecycle)
  └── agent_memory.memory_embeddings (memory_id, embedding_model, embedding_version — PK composite)

knowledge.knowledge_sources (id PK, authority_class)
  └── knowledge.source_versions (source_id, version — UNIQUE, content_hash)
        └── knowledge.knowledge_chunks (source_version_id FK)
              └── knowledge.chunk_embeddings (chunk_id, embedding_model, embedding_version — PK composite)

control_plane.* (services/cosa, TypeScript — schema riêng, KHÔNG chung với các schema Python ở trên)
  missions → tasks → assignments (unique partial index: 1 task chỉ 1 assignment 'leased')
  workers → runtime_leases (1 run_id : 1 lease)
  scheduled_tasks (coalescing_key unique khi status='scheduled')
  watches → trigger_policies, watches → signal_observations (dedupe_key unique)
  delivery_policies → delivery_attempts
  cost_ledger
```

## Nguyên tắc ID

- Python schemas: chủ yếu `VARCHAR` string ID tự sinh dạng `<prefix>_<uuid4 hex rút gọn>` (vd `run_xxxx`, `call_xxxx`, `claim_xxxx`).
- TypeScript schemas (`cosa`, `control_plane`): `BIGINT` snowflake ID (`generateSnowflake()`) cho entity nội bộ TS, `TEXT` cho ID tham chiếu từ Python (vd `runtime_leases.run_id`).

## Composite key quan trọng nhất

`(run_id, tool_call_id)` — xuất hiện ở `run_tool_calls`, `approvals`, `invocation_governance_state`. Đây là identity không được phép tách rời hoặc tự sinh lại ở bất kỳ tầng nào (xem `ADR-DURABLE-IDENTITY.md`).
