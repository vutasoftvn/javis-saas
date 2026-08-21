# COSA Startup Co-founder Methodology — Integration Analysis

**Status:** Phase 0 deliverable — intermediate document, superseded by `COSA_STARTUP_COFOUNDER_METHODOLOGY.md` at the end of Phase 9 (see roadmap below). Do not treat this as long-term canonical reference.

**Source input:** `markdown/COSA_STARTUP_COFOUNDER_METHODOLOGY_SUPPLEMENT.md` (draft v1.0, methodology proposal derived from the AIS4EE handbook).

**Purpose:** Verify the Supplement's architecture claims against the actual codebase, resolve overlap with `markdown/untitled folder/COSA_Stage_Aware_Startup_Operating_Architecture.md`, and define a concrete integration roadmap that extends existing COSA components instead of creating parallel ones (per `CLAUDE.md` §1, §14).

---

## 1. Key finding: two overlapping architecture docs, not one

`COSA_STARTUP_COFOUNDER_METHODOLOGY_SUPPLEMENT.md` and `COSA_Stage_Aware_Startup_Operating_Architecture.md` both independently define per-stage questions, gates, artifacts, and metrics for S0–S6. They are not true duplicates — they operate at different layers — but implementing either in isolation would create two sources of truth for the same methodology.

| | Stage-Aware Architecture (existing) | Supplement (new) |
|---|---|---|
| Focus | **Outer layer**: per-stage governance, artifacts, metrics, frameworks to use/avoid | **Inner layer**: how to ask, how to classify epistemic state, how to weigh evidence |
| Breadth | Wide — business-model-specific metric variants (B2B/SaaS/e-commerce), explicit "avoid" lists per stage | Narrow but deep — mainly problem/solution validation |
| Question depth | One headline question per stage | Full Question Graph (Q1–Q10 for S1) with `question_type`, follow-ups, evidence policy |
| Evidence model | Metric lists only | Full evidence hierarchy (belief → desk research → interview → time investment → deposit → payment) + anti-bias rules |
| Gate | Qualitative multiplicative formula | Multi-state gate outcome (`PASS/CONDITIONAL_PASS/TEST_MORE/CHALLENGED/FAIL`) + separate founder decision |
| **Match with existing code** | **High** — structure mirrors `StagePolicySpec` in `backend/app/founder_os/strategy/schemas/stage_schemas.py` almost 1:1 (primary_goal, primary_questions, required_entities, primary_metrics, deemphasized_tools, recommended_methods, priority_agents). Likely the original source that seeded this schema. | No existing code counterpart — this is genuinely new. |

**Decision: layer, don't merge.**
- Stage-Aware Architecture doc = canonical **outer layer** (artifact/metric/framework/gate per stage) — already reflected in `StagePolicySpec`.
- Supplement's Question Graph (§14) + epistemic classification (§15) + evidence hierarchy (§7.7) + anti-bias rules (§17.4) = canonical **inner layer**, plugged into `StagePolicySpec.primary_questions` / `required_entities`.

## 2. Claim-vs-codebase verification

| Claim | Codebase reality | Verdict |
|---|---|---|
| `Project.project_stage` = S0–S6 | `backend/core/strategy/project.py:30`, string field, default `S1_PROBLEM_VALIDATION` | Confirmed |
| Two competing stage vocabularies exist, need audit | `core.validation.enums.ProjectStage` (IDEA/VALIDATION/MVP/...) exists in `backend/core/validation/enums.py` with no found consumer | Confirmed, but... |
| No third vocabulary should be created | Already unified: `ProjectStageEnum` in `backend/app/founder_os/strategy/schemas/stage_schemas.py` merges both vocabularies with an explicit "Legacy stage codes for backward compatibility" comment | Better than assumed — no new compat layer needed |
| Validation chain (`ValidationAssumption→...→ValidationDecision`) | Fully implemented, `backend/core/validation/evidence_chain.py`, exposed via `backend/app/founder_os/validation/router.py` | Confirmed, reuse as-is |
| Strategy `Hypothesis`/`Evidence` overlaps Validation chain | Confirmed in `backend/core/strategy/evidence.py` (evidence ladder E0–E6). Different purpose, but no documented boundary | Confirmed gap — needs ADR |
| `StageTransitionAudit`, `PrematureScalingAlert`, `NextActionCandidate/Ranking` | Fully implemented in `backend/core/strategy/project.py` and `next_action.py`, own routers | Confirmed, extend only |
| `MethodologyPlan`, `WorkspaceTemplateVersion.config_jsonb` | Implemented in `methodology.py` / `templates.py` | Confirmed, usable for Question Graph storage |
| Customer discovery models (`VerbatimQuote`, `PainPattern`, `EarlyAdopterCandidate`, `ProblemSeverityScorecard`, `QuestionTypeEnum`, `EpistemicType`) | All implemented in `backend/core/validation/customer_discovery.py` / `enums.py` | Confirmed, reuse as-is |
| Co-founder Operating Loop needs an orchestrator | `AdkCofounderOrchestrator` already exists and is functional at `backend/app/workforce/agents/orchestration/` (mission control, 5-domain specialist delegation, pause/resume) — the Supplement doesn't mention this component | Real gap is a missing *node* in the existing pipeline, not a new orchestrator |
| Knowledge just-in-time coaching | Foundation exists (`backend/app/platform/vault/`: embedding, retrieval, chunking, graph service) but lacks stage/dimension/regulatory_sensitivity metadata | Confirmed gap |
| Frontend stage workspace | `frontend/lib/modules/strategy/views/project_stage_workspace_view.dart` exists, currently renders only Service Assessment + Week-13 Gate | Confirmed gap — no evidence-chain or State Snapshot UI yet |
| Frontend has partial validation UI plumbing | Flutter/GetX. `validation_service.dart` has `ValidationAssumptionModel` + `getRiskiestAssumptions()`; `strategy_controller.dart` has `ceoNextActions` | Confirmed, extend rather than rebuild |
| Old root `skills/`, `workflows/`, `tools/`, `executors/` scaffolds should not be recreated | Confirmed removed 2026-08-21 per canonical ownership map | Supplement's own warning is correct |

## 3. Correction (post Phase 0): most of the "gap list" below was already built

A deeper audit after this document's first version found that `backend/app/founder_os/validation/` already implements almost the entire S1 vertical slice described in the Supplement: `interview_service.py` (LLM-driven Classify→Structure→Ask loop), `question_auditor_service.py` (anti-bias question classifier, §7.4/§17.4), `risk_service.py` (risk matrix, AI hypothesis builder, experiment recommender, solution-bias detector, §8.2/§8.4/§18), `customer_discovery_service.py` + `problem_intelligence_service.py` (quote extraction, role coverage, problem scorecard, pattern/niche/shock autopsy, §7.5–§7.7/§17). All of this is exposed via 44 endpoints in `backend/app/founder_os/validation/router.py`, and the frontend (`validation_service.dart` + the `ValidationStudioTab`, wired into `StrategyView` → live via `dashboard_view.dart`) already calls and renders most of it. Original Phase 2, most of Phase 3, and Phase 6 of the integration plan were consequently obsolete before being written — see the approved plan at the path referenced in §4 for what was actually built vs skipped.

A second discovery (ADR-008) found **four independent "next best action" implementations** with no awareness of each other: `core.strategy.next_action` (`NextActionCandidate`/`NextActionRanking`, embedded in the main chat AI's prompt context and a realtime voice tool — genuinely live, not a dashboard duplicate), `validation.review_service.synthesize_single_next_best_action` (unwired to any UI), `CosaCofounderService.get_next_best_action` (the only one rendered to users today, via `Top3FocusWidget` in `HologramHubView`), and three frontend widgets of which two (`next_actions_panel.dart`, `next_best_actions_card.dart`) were fully dead and have been deleted. See ADR-008 for the full boundary decision — no backend system was retired, because one that looked "dead" during the first pass turned out to be a live dependency of the main chat/voice AI.

## 4. Real gaps confirmed to still require code

1. **Question Graph — done for all stages S0–S6 (62 nodes).** See ADR-010. Content lives as versioned code in `backend/app/founder_os/validation/question_graph.py` (not `WorkspaceTemplateVersion.config_jsonb`, which already has a different live owner — `TemplateService`'s capability packs). Deterministic selection (`question_graph_service.py`) defaults to each stage's own sequence, overridden only when a linked `ValidationAssumption` hits the existing Critical Risk threshold (risk_score >= 16). Wired into `ValidationInterviewService.process_user_turn`'s prompt as a non-binding suggestion, exposed standalone via `GET /projects/{project_id}/validation/next-question`, and surfaced in the `validation.get_snapshot` chat tool. S1 follows the Supplement's explicit Q1–Q10; S0/S2–S6 were decomposed by hand from headline questions + topic lists since the Supplement has no equivalent numbered breakdown for those stages.
2. **ADK Orchestrator ↔ Validation interview loop bridge — done (partial, by design).** See ADR-009. Rather than merging session models or adding an ADK workflow node, a new read-only tool (`validation.get_snapshot`, `backend/app/founder_os/validation/validation_tools.py`) was registered in the canonical tool registry so the *already-live* general chat surface (`chat_execution_service.py`, embedded in `HologramHubView`) can answer validation-status questions inline. Mission dispatch continues to go through the existing `chat.propose_action` → NeedsYouItem queue, unchanged. `ValidationInterviewService`'s write path is untouched, still only reachable via its own `/validation/chat` session.
3. **Knowledge vault metadata — done.** See ADR-011. Added to `VaultDocument` (the model actually in the live RAG path — `KnowledgeObject`, a separate curated-knowledge feature, is not wired into chat retrieval and was left untouched): `stage`, `dimension`, `regulatory_sensitivity`, `source_version`, `last_verified` (migration `v13_062_vault_document_metadata`). `retrieval_service.search_chunks` gained optional stage/dimension filtering and staleness flagging, wired into `ValidationInterviewService` as a just-in-time coaching block scoped to the current Question Graph node. Existing Vault content is not backfilled with these tags — that's a separate authoring task.

## 5. Roadmap status

Original plan at `/Users/mivacorp/.claude/plans/ph-n-t-ch-chi-ti-t-quiet-wadler.md`. Actual status after the deeper audit:

- **Phase 1 — done.** ADR-007 written (Strategy.Evidence vs Validation chain boundary); `core.validation.enums.ProjectStage` retired and migrated to `ProjectStageEnum` (was a live fallback dependency in 2 files, not dead code as first assumed — see git history on `founder_os/validation/service.py` and `review_service.py`).
- **Phase 2 (Question Graph) — done for S0–S6**, shipped as versioned code (`question_graph.py`) instead of `WorkspaceTemplateVersion.config_jsonb` as originally planned — see ADR-010 for why.
- **Phase 3 (Classify/Challenge/Ask node) — superseded, and the bridge is now done.** The LLM-driven version of this loop already exists in `ValidationInterviewService.process_user_turn`. The bridge to the ADK orchestrator (gap #2) shipped as a read-only tool (ADR-009) rather than a workflow node.
- **Phase 4 (Next Best Action rules) — superseded, and expanded into ADR-008.** Discovered 4 independent next-action systems instead of 1 needing extension. No system was extended or retired except deleting 2 fully-dead frontend widgets (`next_actions_panel.dart`, `next_best_actions_card.dart`). See ADR-008.
- **Phase 5 (Knowledge metadata) — done.** Shipped on `VaultDocument` (not a new table), with a real migration and staleness/filter logic wired into the interview loop — see ADR-011.
- **Phase 6 (Frontend evidence-chain UI) — already built.** `ValidationStudioTab` (Risk Matrix / Hypotheses & Experiments / Evidence Ledger) is live via `StrategyView` → `dashboard_view.dart`. `ProjectValidationCard` (a richer State Snapshot widget) exists but is not wired into any screen — wiring it in is a UI-integration task for whoever picks it up next, not a rebuild.
- **Phase 7 (vertical slice E2E) — effectively already running** through the existing validation module + `ValidationStudioTab`; no separate slice needs to be built.
- **Phase 8/9 (archive source docs, write as-built canonical doc) — not started**, unchanged, still make sense once Phase 2/3(bridge)/5 land.

## 6. Reference table

| Requirement | Existing owner | Action |
|---|---|---|
| Stage enum (canonical) | `backend/app/founder_os/strategy/schemas/stage_schemas.py` (`ProjectStageEnum`) | Keep |
| Stage enum (duplicate) | `backend/core/validation/enums.py` (`ProjectStage`) | Grep + retire (Phase 1) |
| Validation chain | `backend/core/validation/evidence_chain.py` + `backend/app/founder_os/validation/router.py` | Extend (Phase 2–4) |
| Strategy evidence ladder | `backend/core/strategy/evidence.py` | Keep, document boundary (Phase 1) |
| Stage gate / premature scaling | `backend/core/strategy/project.py` | Keep as-is |
| Next action engine | `backend/core/strategy/next_action.py` | Extend rules (Phase 4) |
| Question Graph storage | `backend/core/strategy/templates.py` (`WorkspaceTemplateVersion.config_jsonb`) | Use (Phase 2) |
| Co-founder orchestrator | `backend/app/workforce/agents/orchestration/` | Add node (Phase 3) |
| Knowledge vault | `backend/app/platform/vault/` (`VaultDocument`, `retrieval_service.py`) | Done — metadata + staleness (ADR-011) |
| Frontend stage workspace | `frontend/lib/modules/strategy/views/project_stage_workspace_view.dart` | Extend UI (Phase 6) |
| Frontend validation service | `frontend/lib/modules/strategy/services/validation_service.dart` | Extend (Phase 6) |
| Customer discovery models | `backend/core/validation/customer_discovery.py` | Reuse (Phase 7) |
