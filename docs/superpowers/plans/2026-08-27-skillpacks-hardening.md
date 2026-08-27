# Skillpacks Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm toàn bộ local skillpack hợp lệ, nhất quán và trung thực về tool contract; đưa validator vào quality gate mà không tự động biến Markdown/YAML thành runtime capability.

**Architecture:** skillpacks/ là source material được review, không phải runtime loader. Python validator đọc manifest.yaml và SKILL.md bằng PyYAML, kiểm tra contract tĩnh và trả lỗi có đường dẫn rõ ràng. COSA chỉ có thể dùng skill sau một publish immutable riêng vào SkillSpec và pin hash vào AgentSpec; Phase B đó không nằm trong plan này.

**Tech Stack:** Python 3.11, PyYAML đã có trong packages/agent_core requirements, pytest, Make, GitHub Actions, Markdown và YAML.

**Spec:** docs/superpowers/specs/2026-08-27-skillpacks-hardening-design.md

## Global Constraints

- Scope thực thi là Phase A static contract hardening. Không tạo runtime file loader, auto-publish, auto-pin hay capability mới trong COSA.
- Giữ metadata.id làm business identity ổn định. Frontmatter name là discovery name dẫn xuất, không phải alternate runtime ID.
- Canonical frontmatter name: lowercase; thay . và _ bằng -; gộp các dấu - liên tiếp; phải unique trong toàn bộ skillpacks.
- Mỗi skillpack có đúng manifest.yaml và SKILL.md trong cùng thư mục; manifest root luôn là mapping, source.path là repository-relative folder, runtime.entrypoint là SKILL.md.
- Allowed Tool Calls và runtime.tools là một contract hai chiều. Chỉ ghi ID capability thực; instruction phải nêu fallback không-mutating nếu capability chưa được active cho run.
- Không ghi đè các sửa đổi hiện có ở skillpacks/tasks/manifest.yaml, skillpacks/tasks/SKILL.md và skillpacks/okr/SKILL.md một cách mù quáng. Dùng chúng làm starting snapshot, sau đó đưa về contract đã chốt.
- Validator thuộc packages/agent_core chỉ làm static parsing, không import services/ hoặc apps/. CI có thể gọi script mỏng ở scripts/ với PYTHONPATH repo root.
- Phase B chỉ được lập kế hoạch sau khi Workspace-first tenancy implementation hoàn thành Task 1–8 và workspace tenant isolation suite xanh.

---

## File map

| File | Trách nhiệm sau điều chỉnh |
| --- | --- |
| packages/agent_core/skills/skillpack_contract.py | API parse/validate thuần Python cho source skillpack, không runtime load. |
| tests/agent_core/skills/test_skillpack_contract.py | Cases malformed manifest, entrypoint, frontmatter, naming, path, tool contract và actual repository packs. |
| scripts/validate_skillpacks.py | CLI deterministic trả exit non-zero và diagnostics theo file cho local/CI. |
| Makefile | Target skillpacks-validate và quality invocation rõ ràng. |
| .github/workflows/quality.yml | Chạy validator sau dependency setup ở agent-core quality job. |
| docs/features/skills.md | Nêu rõ source pack validated khác runtime-enabled, và điều kiện Phase B. |
| skillpacks/{tasks,okr,twelve-week-year,core,marketing,strategy}/**/{manifest.yaml,SKILL.md} | 16 pack hợp lệ về YAML/frontmatter/path/name/entrypoint/tool wording. |

---

### Task 1: Xây static contract validator bằng test-first

**Files:**

- Create: packages/agent_core/skills/skillpack_contract.py
- Create: tests/agent_core/skills/test_skillpack_contract.py
- Create: scripts/validate_skillpacks.py

**Interfaces:**

- Produces validate_skillpack_tree(root: Path) -> list[SkillpackViolation].
- Each violation contains path, rule and message; CLI prints one violation per line and exits 1 if any exist.
- Validator only accepts repository relative source.path values below skillpacks/ and never reads a file outside the submitted root.

- [ ] **Step 1: Write failing unit and repository-contract tests**

Build temporary pack trees in tests for each invalid condition, then add one test that validates the real repository root:

~~~python
violations = validate_skillpack_tree(REPO_ROOT / "skillpacks")
assert violations == []
~~~

The fixtures must cover a YAML sequence root, absent frontmatter, invalid dotted/underscored name, duplicate normalized name, missing/non-SKILL entrypoint, mismatched source.path, missing required manifest section, non-string runtime tool, an Allowed Tool Call absent from runtime.tools, and a declared runtime tool that the instruction neither calls nor explicitly marks optional.

- [ ] **Step 2: Verify the current static failures**

Run:

~~~bash
PYTHONPATH=. .venv/bin/pytest tests/agent_core/skills/test_skillpack_contract.py -q
~~~

Expected: current source fails at least for the array-root tasks manifest, instructions entrypoints, missing core/marketing frontmatter and non-normalized Strategy/12-week names. Preserve this failing output as the repair baseline; do not alter app runtime code to make it pass.

- [ ] **Step 3: Implement a pure parser and validator**

Use yaml.safe_load for manifest and a small explicit parser for the opening YAML frontmatter of SKILL.md. Do not use a permissive Markdown pattern that accepts frontmatter in the middle of a file. Core shape:

~~~python
@dataclass(frozen=True)
class SkillpackViolation:
    path: Path
    rule: str
    message: str

def normalize_discovery_name(value: str) -> str:
    value = re.sub(r"[._]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", value).strip("-")
~~~

Require apiVersion, kind, metadata, publisher, source, capability, runtime, permissions, risk and trust as mappings/expected scalar types. Validate only the local static contract; do not test availability of a capability in build_cosa_agent_plane here.

- [ ] **Step 4: Add a deterministic command-line boundary**

scripts/validate_skillpacks.py should resolve the repository root relative to itself, invoke validate_skillpack_tree(root / "skillpacks"), print path:rule:message, and return 0 only for no violations. It must never modify a manifest or Markdown file.

- [ ] **Step 5: Run validator unit tests**

Run:

~~~bash
PYTHONPATH=. .venv/bin/pytest tests/agent_core/skills/test_skillpack_contract.py -q
PYTHONPATH=. .venv/bin/python scripts/validate_skillpacks.py
~~~

Expected: unit fixtures exercise each error class; real-tree command remains red until Task 2 repairs the source.

- [ ] **Step 6: Commit**

~~~bash
git add packages/agent_core/skills/skillpack_contract.py tests/agent_core/skills/test_skillpack_contract.py scripts/validate_skillpacks.py
git commit -m "test: define static skillpack contract"
~~~

### Task 2: Repair all 16 packs without changing their stable identities

**Files:**

- Modify: skillpacks/tasks/{manifest.yaml,SKILL.md}
- Modify: skillpacks/okr/{manifest.yaml,SKILL.md}
- Modify: skillpacks/twelve-week-year/{manifest.yaml,SKILL.md}
- Modify: skillpacks/core/weekly-review/{manifest.yaml,SKILL.md}
- Modify: skillpacks/marketing/{campaign-review,copywriting,market-research,positioning,seo-plan}/{manifest.yaml,SKILL.md}
- Modify: skillpacks/strategy/{assumption-discovery,decision-capture,evidence-synthesis,experiment-design,gate-evaluation,next-best-action,stage-assessment}/{manifest.yaml,SKILL.md}
- Modify: tests/agent_core/skills/test_skillpack_contract.py

**Interfaces:**

- Every manifest is a mapping and keeps its existing metadata.id, version and source identity.
- Every SKILL.md begins with valid name/description frontmatter and uses its normalized discovery name.
- Every manifest lists runtime.entrypoint: SKILL.md and runtime.tools as an explicit list of capability ID strings.

- [ ] **Step 1: Turn the audit facts into exact expected assertions**

Extend the real-tree test to assert the repaired facts before modifying source:

~~~python
assert manifest["runtime"]["entrypoint"] == "SKILL.md"
assert frontmatter["name"] == normalize_discovery_name(manifest["metadata"]["id"])
assert manifest["source"]["path"] == pack.relative_to(REPO_ROOT).as_posix()
~~~

For packs whose canonical metadata ID does not map one-to-one to directory name, assert the documented source.path rather than rewriting business IDs.

- [ ] **Step 2: Verify current failure remains specific**

Run:

~~~bash
PYTHONPATH=. .venv/bin/python scripts/validate_skillpacks.py
~~~

Expected: diagnostics name every malformed pack and rule, including tasks root mapping rather than failing later with an attribute/type error.

- [ ] **Step 3: Normalize manifest and frontmatter mechanics**

Restore skillpacks/tasks/manifest.yaml to a top-level mapping. Change OKR and Twelve Week Year entrypoints to SKILL.md. Add opening frontmatter to core/weekly-review and every marketing skill. Normalize names, for example:

~~~yaml
---
name: operations-twelve-week-year
description: Hướng dẫn quản trị thực thi chu kỳ 12 tuần theo workspace.
---
~~~

Keep metadata.id values such as operations.okr, operations.tasks and strategy.assumption-discovery unchanged. Do not use shortened names such as okr or tasks as the final discovery convention because they make the global identity ambiguous.

- [ ] **Step 4: Reconcile each instruction with its actual declared tools**

For each Allowed Tool Calls section:

1. extract actual capability IDs, not HTTP route names or pseudo aliases;
2. list precisely those executable calls under runtime.tools;
3. make a listed optional prerequisite explicit in prose if it is not an executed call;
4. replace an unregistered write directive with the mandated fallback: explain that execution is unavailable, provide a non-mutating plan, and do not claim a write occurred.

For strategy/decision-capture, treat an existing gateEvaluationId as caller-provided context, not a hidden tool call. For strategy/gate-evaluation, do not declare stage-policy lookup as executable until a real capability contract exists. Cross-references to another skill never count as a tool call.

- [ ] **Step 5: Run the real source contract**

Run:

~~~bash
PYTHONPATH=. .venv/bin/python scripts/validate_skillpacks.py
PYTHONPATH=. .venv/bin/pytest tests/agent_core/skills/test_skillpack_contract.py -q
~~~

Expected: all 16 packs pass; tool wording contains neither pseudo-tool aliases nor claims that a local pack granted runtime access.

- [ ] **Step 6: Commit**

~~~bash
git add skillpacks tests/agent_core/skills/test_skillpack_contract.py
git commit -m "fix: normalize local skillpack contracts"
~~~

### Task 3: Put static validation in the normal quality gate

**Files:**

- Modify: Makefile
- Modify: .github/workflows/quality.yml
- Modify: tests/agent_core/skills/test_skillpack_contract.py

**Interfaces:**

- Produces make skillpacks-validate, which runs the CLI with repository PYTHONPATH and has no network or database requirement.
- verify invokes skillpacks-validate before app integration suites.
- GitHub Actions runs the same command in the agent-core job after installing packages/agent_core/requirements.txt.

- [ ] **Step 1: Add a failing target invocation test**

Add a test/command assertion that invokes the script through Make, not only directly. Keep a fixture invocation that points the CLI at a deliberately malformed temporary root and asserts non-zero:

~~~python
assert subprocess.run(command, cwd=REPO_ROOT).returncode == 1
~~~

- [ ] **Step 2: Verify no normal quality target protects skillpacks yet**

Run:

~~~bash
make skillpacks-validate
~~~

Expected: make reports that the target does not yet exist.

- [ ] **Step 3: Add local and CI gates**

Add:

~~~make
skillpacks-validate:
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/python scripts/validate_skillpacks.py
~~~

Include it in verify after boundary-check and before expensive integration tests. Add a workflow step with equivalent PYTHONPATH command, using the existing agent-core dependency installation that already includes PyYAML. Do not introduce a separate JavaScript/Ruby YAML parser or network install.

- [ ] **Step 4: Prove local and CI-equivalent invocation**

Run:

~~~bash
make skillpacks-validate
PYTHONPATH=. .venv/bin/pytest tests/agent_core/skills/test_skillpack_contract.py -q
PYTHONPATH=. .venv/bin/pytest tests/agent_core packages/agent_testkit -q
~~~

Expected: a valid repository passes each command; a malformed fixture remains rejected; Agent Core package boundary remains intact.

- [ ] **Step 5: Commit**

~~~bash
git add Makefile .github/workflows/quality.yml tests/agent_core/skills/test_skillpack_contract.py
git commit -m "ci: validate skillpack contracts"
~~~

### Task 4: Record the runtime boundary and a safe Phase B release prerequisite

**Files:**

- Modify: docs/features/skills.md
- Modify: docs/superpowers/specs/2026-08-27-skillpacks-hardening-design.md
- Modify: tests/agent_core/skills/test_skillpack_contract.py
- Modify: apps/cosa/composition/agent_plane.py

**Interfaces:**

- Documents that a validated local skillpack is source-only and not executable.
- Produces a regression assertion that COSA agent-plane construction does not scan skillpacks/ or register capabilities from local Markdown/YAML.
- Records Phase B prerequisite: Workspace-first tenancy plan Task 1–8 green, then capability-first vertical slice selected explicitly.

- [ ] **Step 1: Add a failing no-local-loader regression test**

Add a source-boundary test that constructs the existing plane with fakes and asserts changing/adding a temporary local skillpack cannot change registered capability IDs:

~~~python
assert "operations.task.list" in plane.capability_registry
assert all("skillpacks" not in str(source) for source in inspected_runtime_sources)
~~~

The test must not introduce a loader to satisfy itself; it protects the intentional absence of one.

- [ ] **Step 2: Verify existing runtime registration is explicit**

Run:

~~~bash
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa -q
rg -n 'skillpacks|operations.task.list|operations.task.read' apps/cosa/composition packages/agent_core
~~~

Expected: capability registration is explicit in build_cosa_agent_plane and there is no local skillpack runtime consumer.

- [ ] **Step 3: Make the source/runtime distinction durable**

Document the following release conditions:

1. Phase A validator passing means reviewed reference material only.
2. A Phase B candidate needs a real capability handler with Workspace authorization, policy, approval and audit.
3. The capability must be registered in build_cosa_agent_plane and integration-tested before it appears in SkillSpec.required_capabilities.
4. Publishing calls publish_skill_spec and pins an exact PinnedSkillRef hash/version; local edit never mutates a run.
5. No Phase B work starts until the Workspace-first tenant migration and isolation gate complete.

Keep agent_plane.py free of local source discovery; only adjust comments or an explicit guard test hook if required by the test.

- [ ] **Step 4: Run source and runtime boundary tests**

Run:

~~~bash
make skillpacks-validate
PYTHONPATH=. .venv/bin/pytest tests/agent_core/skills tests/apps/cosa -q
make boundary-check
~~~

Expected: all source packs are valid, local source remains non-executable, and no architecture boundary changes.

- [ ] **Step 5: Commit**

~~~bash
git add docs/features/skills.md docs/superpowers/specs/2026-08-27-skillpacks-hardening-design.md tests/agent_core/skills/test_skillpack_contract.py apps/cosa/composition/agent_plane.py
git commit -m "docs: define skillpack runtime activation boundary"
~~~

## Final acceptance checklist

- [ ] All 16 local packs contain exactly one valid mapping manifest and one valid SKILL.md with canonical frontmatter.
- [ ] metadata.id remains stable; normalized frontmatter names are unique and not alternate runtime IDs.
- [ ] Every declared executable tool has an exact runtime.tools string, every declared tool is used or explicitly optional, and unavailable actions instruct a non-mutating fallback.
- [ ] make skillpacks-validate and CI reject malformed YAML, invalid entrypoints, absent frontmatter, name collisions, path drift and tool-contract drift.
- [ ] COSA has no local skillpack loader, automatic publish, automatic pin or permission grant.
- [ ] Runtime activation remains a separate capability-first release after Workspace-first tenancy is complete.
