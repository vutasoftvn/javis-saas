# Skillpack Production Readiness Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make every built-in skillpack deployable, governed by a fail-closed contract, present in the registry before a COSA agent runs, and backed by a versioned evaluation-contract asset.

**Architecture:** API and worker images package an immutable copy of the built-in bundle at /app/skillpacks. A common startup bootstrap validates and publishes the bundle idempotently to the durable spec registry, then resolves every pinned skill before serving or polling. Contract validation becomes strict: built-ins need explicit governance and valid evaluation assets; the admin sync endpoint reuses the bootstrap but is never the production prerequisite.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, PyYAML, pytest, Docker Compose, PostgreSQL spec registry.

**Spec:** docs/superpowers/specs/2026-08-31-codebase-quality-academy-production-design.md is the parent production-quality design. This plan adds the skillpack runtime and contract scope deliberately excluded from that document.

## Global Constraints

- Do not edit the active Claude Code domain move. It owns relocation of tasks, twelve-week-year, and okr to skillpacks/operations.
- Built-in startup fails closed for missing source, contract violation, parse failure, or pin/hash mismatch.
- The registry is immutable: changing a published skill definition requires increasing that pack's manifest version and updating an intentional pin.
- API and worker must run without a founder or admin first calling an HTTP sync endpoint.
- Keep packages/agent generic. COSA injects its actual capability inventory at the application boundary.
- Policy-evaluation YAML proves contract coverage only; it is not evidence that an LLM behavioural evaluation has run.
- Make a focused commit after each task; never sweep the current dirty worktree into a commit.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| apps/cosa/agents/skillpack_seed.py | Locate, validate, parse, and idempotently publish built-in skillpacks. |
| apps/cosa/agents/seed.py | Compose skill, prompt, model-policy, and AgentSpec initialization. |
| apps/cosa/agents/specs.py | Export deployed AgentSpecs for pin verification. |
| apps/cosa/api/app.py and apps/cosa/worker/main.py | Run common initialization before traffic or worker polling. |
| apps/cosa/api/skill_registry_routes.py | Reuse the seed operation for manual authorized sync. |
| apps/cosa/Dockerfile.api and apps/cosa/Dockerfile.worker | Package bundle, eval assets, and attribution ledger. |
| packages/agent/skills/skillpack_contract.py | Validate manifest, governance, tools, and eval paths. |
| packages/agent/skills/eval_contract.py | Parse declarative policy-evaluation suites. |
| apps/cosa/api/skillpack_mapper.py | Map only complete valid data; no governance fallbacks. |
| evals/**/*.yaml | One evaluation-contract suite per built-in skillpack. |

## Task 1: Accept the concurrent Operations domain relocation

**Status: completed** — regression landed in `fb395946` after the concurrent
domain relocation was merged.

**Files:**

- Modify: tests/agent/skills/test_skillpack_contract.py
- Inspect only until Claude finishes: skillpacks/operations/tasks, skillpacks/operations/twelve-week-year, skillpacks/operations/okr

**Interfaces:**

- Consumes: Claude Code's completed domain relocation.
- Produces: a regression assertion that id, domain, and source path agree.

- [ ] **Step 1: Confirm the owner has completed its change**

    git diff --cached --name-status -- skillpacks/okr skillpacks/tasks skillpacks/twelve-week-year
    git status --short -- skillpacks/operations

Expected: all six files are moved and no parallel rename is started.

- [ ] **Step 2: Write the failing regression test**

    @pytest.mark.parametrize(
        ("relative_path", "skill_id"),
        [
            ("operations/tasks", "operations.tasks"),
            ("operations/twelve-week-year", "operations.twelve_week_year"),
            ("operations/okr", "operations.okr"),
        ],
    )
    def test_operations_pack_source_path_matches_domain(relative_path: str, skill_id: str) -> None:
        manifest = yaml.safe_load((REPO_ROOT / "skillpacks" / relative_path / "manifest.yaml").read_text())
        assert manifest["metadata"]["id"] == skill_id
        assert manifest["capability"]["domain"] == "operations"
        assert manifest["source"]["path"] == f"skillpacks/{relative_path}"

- [ ] **Step 3: Run and commit the independent regression**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py::test_operations_pack_source_path_matches_domain -q

Expected: three passes.

    git add tests/agent/skills/test_skillpack_contract.py
    git commit -m "test: lock operations skillpack paths"

## Task 2: Implement a fail-closed built-in bundle bootstrap

**Status: completed** — bootstrap and pinned-skill resolution landed in
`f7b1402b`.

**Files:**

- Create: apps/cosa/agents/skillpack_seed.py
- Modify: apps/cosa/agents/seed.py
- Modify: apps/cosa/agents/specs.py
- Create: tests/apps/cosa/agents/test_skillpack_seed.py
- Modify: tests/apps/cosa/agents/test_seed.py

**Interfaces:**

- Consumes: SpecRegistryRepository, CapabilityRegistry.list_specs(), validate_skillpack_tree(), parse_skillpack_spec(), and publish_skill_spec().
- Produces: seed_builtin_skillpacks() and seed_cosa_runtime_specs().

- [ ] **Step 1: Write failing startup tests**

    @pytest.mark.asyncio
    async def test_seed_cosa_runtime_specs_resolves_all_pinned_skills(plane: CosaAgentPlane) -> None:
        await seed_cosa_runtime_specs(
            spec_registry=plane.spec_registry,
            capability_registry=plane.capability_registry,
            skillpacks_root=REPO_ROOT / "skillpacks",
        )
        resolver = SkillResolver(plane.spec_registry)
        for agent_spec in COSA_DEPLOYED_AGENT_SPECS:
            resolved = await resolver.resolve(agent_spec.pinned_skills)
            assert [item.id for item in resolved] == [pin.skill_id for pin in agent_spec.pinned_skills]

    @pytest.mark.asyncio
    async def test_seed_cosa_runtime_specs_is_idempotent(plane: CosaAgentPlane) -> None:
        kwargs = {
            "spec_registry": plane.spec_registry,
            "capability_registry": plane.capability_registry,
            "skillpacks_root": REPO_ROOT / "skillpacks",
        }
        await seed_cosa_runtime_specs(**kwargs)
        await seed_cosa_runtime_specs(**kwargs)
        expected_count = len(list((REPO_ROOT / "skillpacks").rglob("manifest.yaml")))
        assert len(await plane.spec_registry.list_all(spec_kind="skill")) == expected_count

Also test that a missing bundle root and a contract violation raise BuiltinSkillpackSeedError; neither may produce partially initialized AgentSpecs.

- [ ] **Step 2: Run to prove the current gap**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/apps/cosa/agents/test_skillpack_seed.py -q

Expected: fail because the startup bootstrap does not exist.

- [ ] **Step 3: Implement bundle discovery and strict publication**

Create apps/cosa/agents/skillpack_seed.py with these public contracts:

    class BuiltinSkillpackSeedError(RuntimeError):
        pass

    def resolve_skillpacks_root(root: Path | None = None) -> Path:
        candidate = root or Path(os.environ.get("COSA_SKILLPACKS_ROOT", "/app/skillpacks"))
        if not candidate.is_dir():
            raise BuiltinSkillpackSeedError(f"Built-in skillpacks are unavailable at {candidate}")
        return candidate.resolve()

    async def seed_builtin_skillpacks(
        spec_registry: SpecRegistryRepository,
        *,
        capability_ids: set[str],
        skillpacks_root: Path | None = None,
    ) -> tuple[PublishedSpecRecord, ...]:
        root = resolve_skillpacks_root(skillpacks_root)
        violations = validate_skillpack_tree(root, registered_capabilities=capability_ids)
        if violations:
            details = "; ".join(f"{item.path}:{item.rule}" for item in violations)
            raise BuiltinSkillpackSeedError(details)
        records: list[PublishedSpecRecord] = []
        for manifest_path in sorted(root.rglob("manifest.yaml")):
            try:
                spec = parse_skillpack_spec(manifest_path.parent)
                record = await publish_skill_spec(
                    spec,
                    repository=spec_registry,
                    publisher="cosa_built_in",
                )
            except Exception as exc:
                raise BuiltinSkillpackSeedError(
                    f"Cannot publish {manifest_path.parent}: {exc}"
                ) from exc
            records.append(record)
        return tuple(records)

The function calls validate_skillpack_tree(root, registered_capabilities=capability_ids), raises one BuiltinSkillpackSeedError if any violation exists, parses every manifest in sorted order, and calls publish_skill_spec with publisher set to cosa_built_in. Any parse or publish failure aborts immediately; do not log and skip a pack.

- [ ] **Step 4: Compose complete runtime initialization**

Export this tuple from apps/cosa/agents/specs.py:

    COSA_DEPLOYED_AGENT_SPECS = (
        COSA_OPERATIONS_AGENT_SPEC,
        COSA_FINANCE_AGENT_SPEC,
        COSA_MARKETING_AGENT_SPEC,
        COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
        COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
    )

Add this public function to apps/cosa/agents/seed.py:

    async def seed_cosa_runtime_specs(
        *,
        spec_registry: SpecRegistryRepository,
        capability_registry: CapabilityRegistry,
        skillpacks_root: Path | None = None,
    ) -> None:
        await seed_builtin_skillpacks(
            spec_registry,
            capability_ids={spec.id for spec in capability_registry.list_specs()},
            skillpacks_root=skillpacks_root,
        )
        await seed_cosa_agent_specs(spec_registry)
        resolver = SkillResolver(spec_registry)
        for agent_spec in COSA_DEPLOYED_AGENT_SPECS:
            await resolver.resolve(agent_spec.pinned_skills)

- [ ] **Step 5: Verify and commit**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/apps/cosa/agents/test_skillpack_seed.py tests/apps/cosa/agents/test_seed.py -q

Expected: pass; a second bootstrap has exactly one published record for every discovered manifest and no hash conflict.

    git add apps/cosa/agents/skillpack_seed.py apps/cosa/agents/seed.py apps/cosa/agents/specs.py
    git add tests/apps/cosa/agents/test_skillpack_seed.py tests/apps/cosa/agents/test_seed.py
    git commit -m "feat: bootstrap built-in skillpacks before agent startup"

## Task 3: Wire API, worker, and operator sync to the shared bootstrap

**Status: completed** — API, worker, fixtures, and authorized manual sync now
share the same bootstrap (`51ca2f01`).

**Files:**

- Modify: apps/cosa/api/app.py
- Modify: apps/cosa/worker/main.py
- Modify: apps/cosa/api/skill_registry_routes.py
- Modify: tests/apps/cosa/test_scheduled_session_worker.py
- Modify: tests/apps/cosa/test_vertical_slice_1_read_path.py
- Modify: tests/apps/cosa/test_vertical_slice_2_write_approval.py
- Modify: tests/apps/cosa/test_workspace_execution_e2e.py
- Modify: tests/apps/cosa/test_skill_registry_routes.py

**Interfaces:**

- Consumes: seed_cosa_runtime_specs() and seed_builtin_skillpacks() from Task 2.
- Produces: no request or worker run begins with unresolved pins; manual sync has identical semantics.

- [ ] **Step 1: Replace fixture-only AgentSpec seeding with complete seeding**

Replace:

    await seed_cosa_agent_specs(spec_repo)

with:

    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
        skillpacks_root=REPO_ROOT / "skillpacks",
    )

Use the plane registry in every fixture; do not seed a separate spec_repo.

- [ ] **Step 2: Run the failing runtime slice**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_vertical_slice_2_write_approval.py tests/apps/cosa/test_workspace_execution_e2e.py -q

Expected before entrypoint wiring: four failures mentioning lifecycle.context-resolver@1.0.0.

- [ ] **Step 3: Initialize before service readiness**

In both API lifespan and worker main(), replace seed_cosa_agent_specs(spec_registry) with:

    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )

Call it after build_cosa_agent_plane() and before event intake setup, API serving, or worker polling.

- [ ] **Step 4: Refactor the protected sync endpoint**

Keep authorization and response model. Replace local validation/publication with seed_builtin_skillpacks(spec_registry, capability_ids=capability_ids), passing:

    capability_ids={spec.id for spec in plane.capability_registry.list_specs()}

Map BuiltinSkillpackSeedError to HTTP 400 and SpecVersionHashConflictError to HTTP 409. A response may not report a partial successful sync.

- [ ] **Step 5: Verify and commit**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_vertical_slice_2_write_approval.py tests/apps/cosa/test_workspace_execution_e2e.py tests/apps/cosa/test_skill_registry_routes.py -q

Expected: pass; no response contains the missing pinned-skill error.

    git add apps/cosa/api/app.py apps/cosa/worker/main.py apps/cosa/api/skill_registry_routes.py
    git add tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_vertical_slice_1_read_path.py
    git add tests/apps/cosa/test_vertical_slice_2_write_approval.py tests/apps/cosa/test_workspace_execution_e2e.py tests/apps/cosa/test_skill_registry_routes.py
    git commit -m "fix: seed skill registry before COSA runs"

## Task 4: Package immutable runtime assets into production images

**Status: completed** — image bundle contract, API/worker copies, and
deployment guidance are included in the implementation that follows this plan
record.

**Files:**

- Modify: apps/cosa/Dockerfile.api
- Modify: apps/cosa/Dockerfile.worker
- Create: deploy/central_vps/smoke/test_skillpack_image_contract.py
- Modify: docs/operations/deployment.md

**Interfaces:**

- Consumes: /app/skillpacks, /app/evals, and /app/docs/integrations/skill-source-attribution.md.
- Produces: production images capable of strict bootstrap without a repository checkout.

- [ ] **Step 1: Write the failing Dockerfile contract**

    @pytest.mark.parametrize("dockerfile", ["apps/cosa/Dockerfile.api", "apps/cosa/Dockerfile.worker"])
    def test_cosa_runtime_image_copies_skillpack_bundle(dockerfile: str) -> None:
        content = (REPO_ROOT / dockerfile).read_text()
        assert "COPY skillpacks /app/skillpacks" in content
        assert "COPY evals /app/evals" in content
        assert "COPY docs/integrations/skill-source-attribution.md /app/docs/integrations/skill-source-attribution.md" in content

- [ ] **Step 2: Implement the image copies**

Add before RUN chown -R app:app /app in both runtime Dockerfiles:

    COPY skillpacks /app/skillpacks
    COPY evals /app/evals
    COPY docs/integrations/skill-source-attribution.md /app/docs/integrations/skill-source-attribution.md

Do not add them to deploy/central_vps/Dockerfile.migrate: migration remains schema-only and must not take ownership of application spec bootstrap.

- [ ] **Step 3: Verify image contents**

    PYTHONPATH=packages:. .venv/bin/python -m pytest deploy/central_vps/smoke/test_skillpack_image_contract.py -q
    docker build -f apps/cosa/Dockerfile.api -t cosa-api-skillpack-smoke .
    docker run --rm --entrypoint sh cosa-api-skillpack-smoke -lc 'test -d /app/skillpacks && test -d /app/evals && test -f /app/docs/integrations/skill-source-attribution.md'
    docker build -f apps/cosa/Dockerfile.worker -t cosa-worker-skillpack-smoke .
    docker run --rm --entrypoint sh cosa-worker-skillpack-smoke -lc 'test -d /app/skillpacks && test -d /app/evals && test -f /app/docs/integrations/skill-source-attribution.md'

Expected: all commands exit 0.

- [ ] **Step 4: Document and commit**

Document: a runtime image contains the versioned bundle; startup publishes it idempotently; changed published definitions need a version bump.

    git add apps/cosa/Dockerfile.api apps/cosa/Dockerfile.worker
    git add deploy/central_vps/smoke/test_skillpack_image_contract.py docs/operations/deployment.md
    git commit -m "fix: package built-in skillpacks in COSA images"

## Task 5: Enforce complete governance and evaluation metadata

**Files:**

- Modify: packages/agent/skills/skillpack_contract.py
- Modify: apps/cosa/api/skillpack_mapper.py
- Modify: tests/agent/skills/test_skillpack_contract.py
- Create: tests/apps/cosa/api/test_skillpack_mapper.py

**Interfaces:**

- Consumes: manifest applicability, autonomy, evidence, and quality fields.
- Produces: mapper and validator rejection rather than silent P0, L0, or read-only defaults.

- [ ] **Step 1: Write failing missing/invalid-field tests**

    @pytest.mark.parametrize("removed", ["applicability", "autonomy", "evidence", "quality"])
    def test_builtin_manifest_requires_governance_sections(removed: str, complete_manifest: dict[str, object]) -> None:
        complete_manifest.pop(removed)
        violations = validate_skillpack_tree(write_pack(complete_manifest))
        assert any(v.rule == f"manifest-missing-{removed}" for v in violations)

    def test_mapper_rejects_missing_governance_metadata(tmp_path: Path) -> None:
        pack_dir = write_minimal_pack(tmp_path, omit="autonomy")
        with pytest.raises(ValueError, match="autonomy"):
            parse_skillpack_spec(pack_dir)

Add cases for invalid lifecycle stage, autonomy level, side-effect class, missing eval file, empty eval suite, and absent required_negative_cases.

- [ ] **Step 2: Implement generic strict validation**

Add these mappings to required_sections:

    "applicability": (dict, "mapping"),
    "autonomy": (dict, "mapping"),
    "evidence": (dict, "mapping"),
    "quality": (dict, "mapping"),

Validate non-empty lifecycle stages, valid stage/ceiling/side-effect enum values, non-negative min_source_refs, boolean self_validation_forbidden, a safe relative evals path existing under the repository root, and a non-empty string-list required_negative_cases.

- [ ] **Step 3: Remove direct-parser defaults**

Replace:

    raw_stages = raw_app.get("project_stages") or ["P0_DISCOVERY"]

with explicit required extraction that raises ValueError before SkillSpec publication.

- [ ] **Step 4: Verify and commit**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py tests/apps/cosa/api/test_skillpack_mapper.py -q

Expected: temporary invalid packs are rejected. The whole tree becomes green in Task 6.

    git add packages/agent/skills/skillpack_contract.py apps/cosa/api/skillpack_mapper.py
    git add tests/agent/skills/test_skillpack_contract.py tests/apps/cosa/api/test_skillpack_mapper.py
    git commit -m "feat: require governed built-in skillpack manifests"

## Task 6: Supply all governance data and policy-evaluation suites

**Files:**

- Modify: affected skillpacks/**/manifest.yaml
- Create: packages/agent/skills/eval_contract.py
- Create: tests/agent/skills/test_skillpack_eval_contract.py
- Create: evals/<domain>/<skill-name>.yaml for every discovered built-in pack
- Modify: evals/README.md

**Interfaces:**

- Consumes: quality.eval_suite and required_negative_cases.
- Produces: one owned, loadable policy-evaluation suite per skillpack.

- [ ] **Step 1: Write the failing whole-tree ownership test**

    def test_every_builtin_skillpack_has_a_valid_owned_eval_suite() -> None:
        for manifest_path in sorted((REPO_ROOT / "skillpacks").rglob("manifest.yaml")):
            manifest = yaml.safe_load(manifest_path.read_text())
            suite = load_skill_eval_suite(REPO_ROOT / manifest["quality"]["eval_suite"])
            assert suite.skill_id == manifest["metadata"]["id"]
            assert suite.skill_version == str(manifest["metadata"]["version"])
            rejected = {case.id for case in suite.cases if case.expected.outcome == "reject"}
            assert set(manifest["quality"]["required_negative_cases"]).issubset(rejected)

- [ ] **Step 2: Define the loader and YAML contract**

Implement load_skill_eval_suite(path: Path) -> SkillEvalSuite. Reject unsupported API version, wrong kind, empty cases, duplicate case ids, missing expected outcome, and outcomes other than accept or reject.

Every YAML file has this shape:

    apiVersion: cosa.ai/skill-eval/v1
    kind: SkillEvalSuite
    skill:
      id: operations.tasks
      version: 2.0.0
    cases:
      - id: accepts-governed-context
        input:
          workspace_id: ws-eval
          project_id: project-eval
        expected:
          outcome: accept
      - id: cross-workspace
        input:
          workspace_id: ws-other
          project_id: project-eval
        expected:
          outcome: reject
          reason: cross-workspace

- [ ] **Step 3: Complete the 26 currently incomplete manifests**

Add explicit lifecycle applicability, autonomy, evidence, quality path, and negative cases to:

    analytics.pmf-scoreboard
    analytics.pmf-survey
    commercial.churn-prevention
    commercial.launch
    commercial.pricing
    commercial.revops
    core.weekly-review
    customer-success.churn-analysis
    customer-success.health-scoring
    discovery.affinity-synthesis
    finance.cfo-review
    growth.experimentation-system
    marketing.campaign-review
    marketing.copywriting
    marketing.market-research
    marketing.seo-plan
    operations.loop-hardening
    platform.skill-adaptation
    product.backlog-prioritization
    product.continuous-discovery
    product.outcome-roadmap
    sales.prospecting
    strategy.evidence-synthesis
    strategy.next-best-action
    strategy.pivot-persevere

If content changes a pinned definition, increment the semantic version and update only its intentional PinnedSkillRef.

- [ ] **Step 4: Create and validate every declared suite**

Create precisely the path declared in each quality.eval_suite. Each suite includes one accepted governed-context case and one rejection per declared negative case. Packs with write/propose tools include rejection for missing evidence or bypassed approval when that is the documented boundary.

Update evals/README.md with schema, validation command, and its non-LLM scope.

    make skillpacks-validate
    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py tests/agent/skills/test_skillpack_eval_contract.py tests/agent/skills/eval/ -q

Expected: every discovered manifest validates, each declared suite file loads, and every negative case is represented.

- [ ] **Step 5: Commit**

    git add packages/agent/skills/eval_contract.py tests/agent/skills/test_skillpack_eval_contract.py
    git add evals skillpacks
    git commit -m "feat: add governed evaluation suites for built-in skillpacks"

## Task 7: Use live capability inventory and distinguish non-callable prose

**Files:**

- Modify: packages/agent/skills/skillpack_contract.py
- Modify: scripts/validate_skillpacks.py
- Modify: apps/cosa/agents/skillpack_seed.py
- Modify: tests/agent/skills/test_skillpack_contract.py
- Modify: skillpacks/growth/ab-testing/SKILL.md
- Modify: other skillpacks/**/SKILL.md only where tool mentions are handoff/reference-only

**Interfaces:**

- Consumes: CapabilityRegistry.list_specs() at the COSA boundary.
- Produces: validation against actual registered capabilities and clear callable/reference-only semantics.

- [ ] **Step 1: Write failing tests**

Test an injected capability set missing a declared tool and expect tool-not-registered. Test this reference-only section passes without adding an implicit permission:

    ## Referenced Capabilities (not callable)
    - finance.transaction.record: hand off to the approved finance flow.

The same capability under Allowed Tool Calls must still fail if undeclared. A capability may not appear in both sections.

- [ ] **Step 2: Remove the generic static COSA capability list**

Application validation always passes:

    {spec.id for spec in plane.capability_registry.list_specs()}

Make this set mandatory for startup and API sync. Update scripts/validate_skillpacks.py to build a deterministic test plane with explicit in-memory repositories and FakeSDKModel, then pass its capability ids. Temporary contract fixtures provide their own test capability set.

- [ ] **Step 3: Correct ambiguous instructions**

For growth/ab-testing, treat metric_contract_ref as supplied context and put analytics.metric_contract.get under Referenced Capabilities (not callable), because its executable boundary is artifact/proposal only and it declares no runtime tools.

Move anti-trigger and handoff mentions such as finance.transaction.record, engagement.message.send, and operations.task.create_draft to the reference-only section. Do not grant permissions just to satisfy a prose parser.

- [ ] **Step 4: Verify and commit**

    make skillpacks-validate
    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py -q

Expected: each callable tool is registered in the actual COSA plane; handoff-only text creates no implied permission.

    git add packages/agent/skills/skillpack_contract.py scripts/validate_skillpacks.py
    git add apps/cosa/agents/skillpack_seed.py tests/agent/skills/test_skillpack_contract.py skillpacks
    git commit -m "fix: validate skillpack tools against live capability inventory"

## Task 8: Gate the release on actual runtime readiness

**Files:**

- Modify: .github/workflows/quality.yml only if commands below are absent
- Modify: docs/operations/deployment.md
- Modify: tests/apps/cosa/agents/test_skillpack_seed.py

**Interfaces:**

- Consumes: all prior tasks.
- Produces: CI/local evidence of bundle, registry, runtime, and production-Compose readiness.

- [ ] **Step 1: Add pin-hash negative coverage**

In test_skillpack_seed.py, make a copied AgentSpec pin an incorrect hash and assert startup verification raises before worker polling. The message includes skill id, version, and hash mismatch.

- [ ] **Step 2: Ensure CI contains all runtime-critical commands**

    make skillpacks-validate
    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py tests/agent/skills/test_skillpack_eval_contract.py tests/agent/skills/eval/ -q
    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/apps/cosa/agents/test_skillpack_seed.py tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_vertical_slice_2_write_approval.py tests/apps/cosa/test_workspace_execution_e2e.py -q
    PYTHONPATH=packages:. .venv/bin/python -m pytest deploy/central_vps/smoke/test_skillpack_image_contract.py -q

- [ ] **Step 3: Run the release gate locally**

    make skillpacks-validate
    make apps-cosa-test
    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py tests/agent/skills/test_skillpack_eval_contract.py tests/agent/skills/eval/ -q
    PYTHONPATH=packages:. .venv/bin/python -m pytest deploy/central_vps/smoke/test_skillpack_image_contract.py -q
    docker compose -f deploy/central_vps/docker-compose.prod.yaml config
    git diff --check

Expected: all commands exit 0. Compose validation uses authorized production-equivalent variables; required secrets are not weakened or replaced with placeholders.

- [ ] **Step 4: Record evidence and commit**

Document build SHA, discovered bundle count, validator result, published skill count, resolved pinned-skill count, and four runtime-slice results. State that bootstrap failure keeps the service unavailable.

    git add .github/workflows/quality.yml docs/operations/deployment.md tests/apps/cosa/agents/test_skillpack_seed.py
    git commit -m "test: gate releases on skillpack runtime readiness"

## Task 9: Add a safe Founder workflow for custom skills

**Files:**

- Modify: apps/cosa/api/skill_schemas.py
- Modify: apps/cosa/api/skill_registry_routes.py
- Modify: packages/agent/skills/candidate_store.py
- Modify: tests/apps/cosa/test_skill_registry_routes.py
- Create: tests/apps/cosa/test_workspace_custom_skill_isolation.py
- Modify: docs/operations/deployment.md

**Interfaces:**

- Consumes: candidate store, validated capability inventory, evaluation-contract loader, authenticated Founder identity.
- Produces: workspace-local custom skills with server-attested evaluation; platform-wide built-ins remain a reviewed repository/deployment change.

- [ ] **Step 1: Write failing tenant and promotion-boundary tests**

    def test_promoted_workspace_custom_skill_is_invisible_to_another_workspace(client: TestClient) -> None:
        create_and_promote_candidate(client, workspace_id="ws-a", skill_name="A-only skill")
        assert not contains_skill(client, workspace_id="ws-b", skill_id="a-only-skill")

    def test_client_cannot_set_its_own_passing_eval_score(client: TestClient) -> None:
        candidate_id = create_candidate(client, workspace_id="ws-a")
        response = client.post(
            f"/agent/skills/{candidate_id}/evaluate",
            json={"eval_score": 1.0, "eval_details": {"claimed": "pass"}},
        )
        assert response.status_code == 422

    def test_founder_cannot_promote_candidate_with_unknown_capability(client: TestClient) -> None:
        candidate_id = create_candidate(
            client,
            workspace_id="ws-a",
            required_capabilities=["not-a-real.capability"],
        )
        assert promote(client, candidate_id).status_code == 400

The test fixture must authenticate ws-a and ws-b separately. It must verify list, get, evaluate, feedback, promotion, and deprecation do not cross workspace boundaries.

- [ ] **Step 2: Define two explicit product paths**

Document and enforce these scopes:

    workspace_custom
      Created by a workspace Founder.
      Stored and published only in that workspace catalogue.
      Default boundary: L0 or L1, artifact/proposal only, no connector, money movement, external send, or lifecycle-transition capability.
      Never automatically pins a global AgentSpec.

    platform_builtin
      Added through repository manifest, SKILL.md, evaluation suite, code review, image build, and the built-in bootstrap.
      May be pinned only after exact hash resolution succeeds.

The custom-skill create request receives scope with a default of workspace_custom. Reject platform_builtin through the public Founder endpoint.

- [ ] **Step 3: Make evaluation server-attested**

Replace client-supplied eval_score with an evaluation request that selects registered cases. The server:

    1. validates the candidate governance and requested capabilities;
    2. runs the deterministic policy-contract cases;
    3. saves evaluator version, case results, timestamp, and computed score;
    4. sets EVALUATED only when every required negative case rejects correctly.

The API returns the server-generated report. A caller cannot pass eval_score or overwrite its provenance.

- [ ] **Step 4: Preserve workspace scope through publication and lookup**

Add workspace scope to the durable candidate/published-custom-skill record. Modify list and get endpoints so a workspace receives built-ins plus its own published custom skills only. Do not call publish_skill_spec into the shared agent_registry.published_specs table for workspace_custom skills unless the schema and every query carry a mandatory workspace key.

Promotion requires founder, an attested passing report, approval reason, valid known capabilities, and a version not already published with a different definition. Deprecation retires only the caller workspace's custom version.

- [ ] **Step 5: Verify and commit**

    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py -q
    PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/skills/test_skillpack_contract.py -q

Expected: Founder can safely create, evaluate, approve, version, retire, and collect feedback on a workspace-local skill; no other workspace can discover or use it.

    git add apps/cosa/api/skill_schemas.py apps/cosa/api/skill_registry_routes.py packages/agent/skills/candidate_store.py
    git add tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py docs/operations/deployment.md
    git commit -m "feat: add governed workspace founder skill workflow"

## Final Definition of Done

- [ ] Every discovered built-in manifest has explicit governance and a valid owned evaluation-contract suite.
- [ ] API and worker images contain immutable bundle, eval files, and attribution ledger.
- [ ] API and worker run the same idempotent bootstrap before traffic or jobs.
- [ ] Every deployed AgentSpec pin resolves with its exact version and definition hash.
- [ ] Missing, malformed, or conflicting packs prevent startup and never produce a partial sync.
- [ ] Tasks, twelve-week-year, and okr are stably located and declared in the Operations domain.
- [ ] Callable tools are validated against the live COSA capability inventory; handoff references are non-callable.
- [ ] Founder-created workspace skills are server-evaluated, founder-approved, tenant-isolated, and cannot become a global AgentSpec pin automatically.
- [ ] All listed CI/local/release checks pass without weakening an existing gate.

## Scope Boundary

This plan does not implement Academy persistence/UI or broader lint, migration, and frontend repairs. Those remain governed by docs/superpowers/specs/2026-08-31-codebase-quality-academy-production-design.md and should be executed as a separate change series after skillpack runtime readiness is stable.
