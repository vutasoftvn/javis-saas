"""Trả về id của một AgentSpec đã publish, đủ để control-plane dispatch.

Discovery (2026-09-02):

- Cả `apps/cosa/api` (lifespan, `apps/cosa/api/app.py`) lẫn worker
  (`apps/cosa/worker/main.py::main`) đều gọi `seed_cosa_runtime_specs(...)` lúc
  boot -> ngay sau khi `real_cosa_stack` lên xanh, bảng
  `agent_registry.published_specs` (migration `packages/agent/migrations/
  007_agent_registry.sql`) đã có sẵn các AgentSpec của COSA:
  `spec_kind='agent'`, `spec_id IN ('cosa.agents.operations',
  'cosa.agents.finance', 'cosa.agents.marketing', 'cosa.agents.customer_support',
  'cosa.agents.customer_support_autopilot')`, `status='published'`
  (xem `apps/cosa/agents/seed.py` + `apps/cosa/agents/specs.py` +
  `packages/agent/registry/publisher.py::publish_agent_spec` dùng `spec_kind="agent"`).
- Vì vậy đường đúng là TRA và trả lại id spec sẵn có, ưu tiên
  `cosa.agents.operations`. Chỉ INSERT spec mới khi (bất thường) chưa có spec
  `agent` nào — khi đó ghi 1 hàng tối thiểu theo schema 007, KHÔNG mock.

`agent_registry.published_specs` là global, không scope theo workspace — tham số
`workspace_id` giữ cho tương thích chữ ký brief và để scenario ghi log, không
tham gia truy vấn. `apps_cosa_base_url` cũng chỉ để scenario tham chiếu.
"""

from __future__ import annotations

import hashlib
import json

from tests.e2e.stack.disposable_postgres import DisposableCluster

_PREFERRED_SPEC_ID = "cosa.agents.operations"


def seed_minimal_agent_spec(
    apps_cosa_base_url: str, cluster: DisposableCluster, *, workspace_id: str
) -> str:
    """Trả về `spec_id` của một AgentSpec `status='published'`.

    Reuse spec do boot seed nếu có (ưu tiên `cosa.agents.operations`); nếu không
    có spec `agent` nào thì INSERT một spec tối thiểu và trả id của nó.
    """
    import psycopg2  # import cục bộ — psycopg2 chỉ có ở job e2e-cross-plane-smoke

    conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT spec_id
                FROM agent_registry.published_specs
                WHERE spec_kind = 'agent' AND status = 'published'
                ORDER BY (spec_id = %s) DESC, published_at ASC
                LIMIT 1
                """,
                (_PREFERRED_SPEC_ID,),
            )
            row = cur.fetchone()
            if row is not None:
                return str(row[0])

            # Fallback (bất thường): chưa có spec agent nào — ghi 1 hàng tối thiểu
            # theo schema migration 007.
            spec_id = "e2e.seed.minimal-agent"
            version = "1.0.0"
            content = {
                "id": spec_id,
                "version": version,
                "kind": "agent",
                "note": "minimal spec seeded by tests/e2e/seed/agent_spec.py fallback",
            }
            content_json = json.dumps(content, sort_keys=True, separators=(",", ":"))
            definition_hash = hashlib.sha256(content_json.encode("utf-8")).hexdigest()
            cur.execute(
                """
                INSERT INTO agent_registry.published_specs
                    (spec_kind, spec_id, version, definition_hash, content, status, publisher)
                VALUES ('agent', %s, %s, %s, %s::jsonb, 'published', 'e2e-seed-kit')
                ON CONFLICT (spec_kind, spec_id, version) DO NOTHING
                """,
                (spec_id, version, definition_hash, content_json),
            )
            return spec_id
    finally:
        conn.close()
