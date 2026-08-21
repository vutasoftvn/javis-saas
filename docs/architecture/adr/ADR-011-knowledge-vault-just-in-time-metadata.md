# ADR 011: Just-in-Time Coaching Metadata on `VaultDocument`, Not `KnowledgeObject`

## Status
Accepted

## Context
The last confirmed gap in the methodology integration analysis was Supplement §20: knowledge should be surfaced "just-in-time" (filtered by stage/dimension, with staleness/regulatory-sensitivity handling) rather than as generic search results, and `backend/app/platform/vault/models.py` had no such metadata.

Before adding fields, checking which model is actually load-bearing for retrieval (per `CLAUDE.md` §14) found two candidate models in the same file: `VaultDocument` (raw file/revision store, chunked and embedded into `document_chunks`) and `KnowledgeObject` (a separate, more structured curated-knowledge/wikilink-graph feature with `object_type`, `status`, `confidence`). Only `VaultDocument` is in the actual RAG path: `retrieval_service.search_chunks` queries `document_chunks` → `vault_revisions` → `vault_documents`, and is called by `chat_execution_service._retrieve_context` — the same live general-chat surface already bridged to validation in ADR-009. `KnowledgeObject`/`knowledge_service.py` is a separate note/decision/lesson graph not wired into chat retrieval at all.

## Decision
1. Metadata lives on `VaultDocument`: `stage` (nullable string, indexed), `dimension` (nullable string), `regulatory_sensitivity` (boolean, default false), `source_version` (nullable string), `last_verified` (nullable date). Migration `alembic/versions/v13_062_vault_document_metadata.py`. All nullable/defaulted so existing documents are unaffected until explicitly tagged.
2. `retrieval_service.search_chunks` gained optional `stage`/`dimension` keyword parameters (default `None` — no filter, so `chat_execution_service._retrieve_context`'s existing call is unchanged) and now returns `regulatory_sensitivity`/`last_verified`/`stale` per chunk. Staleness (`_is_stale`) is a simple, documented policy: a `regulatory_sensitivity` document with no `last_verified` is always stale; otherwise stale past `REGULATORY_STALE_THRESHOLD_DAYS` (180, a placeholder default — no per-workspace configurability requested, so no config table was added for one number, per `CLAUDE.md` "smallest safe change").
3. `ValidationInterviewService.process_user_turn` calls `search_chunks` with the current Question Graph node's `stage`/`dimension` (ADR-010) and injects only non-stale results into the interview prompt as a "KIẾN THỨC LIÊN QUAN" coaching block — this is the concrete just-in-time coaching Supplement §20 describes: knowledge shown because it matches the exact question being asked, not a generic library browse. The call is wrapped in try/except (matching the codebase's existing pattern for optional retrieval, see `_retrieve_context`'s own try/except) so an empty brain or embedding failure degrades to no coaching block, never blocks the interview turn.
4. `KnowledgeObject` is untouched — this ADR does not claim it should be retired or merged; it remains whatever `knowledge_service.py`/`graph_service.py` already use it for.

## Consequences
- No behavior change for the general chat's existing retrieval (`stage`/`dimension` default to `None`); the only new caller that filters is the validation interview loop.
- Tagging documents with `stage`/`dimension`/`regulatory_sensitivity` is a manual/future step — this ADR ships the schema and the filtering/staleness logic, not a backfill or an authoring UI for existing Vault content.
- If `KnowledgeObject` is ever found to need the same just-in-time treatment (e.g. if it gets wired into a different retrieval path later), that is a separate decision — this ADR's metadata additions apply to `VaultDocument` only.
