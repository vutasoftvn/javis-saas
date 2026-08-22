# AgentOS Phase 5 — Marketing Skill Pack (Domain Skill Pack Pilot) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the Skill Layer built in Phase 4 generalizes beyond one toy skill by authoring a real, multi-skill business-domain pack — Marketing (blueprint §23/§44: Research, Positioning, SEO, Copywriting, Analytics) — and add the one piece of router logic Phase 4 didn't need with only a single skill in the catalog: domain-scoped selection, so two skills that legitimately share vocabulary (e.g. "review") in different domains don't collide. Per Phase 5 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4.

**Architecture:** Five new real skillpacks under `skillpacks/marketing/` (`market-research`, `positioning`, `seo-plan`, `copywriting`, `campaign-review`), each a `manifest.yaml` + `SKILL.md` pair discovered and routed by the existing `SkillRegistry`/`SkillRouter`/`SkillInstructionLoader` from Phase 4 — no new subsystem, this phase is content plus one small router extension. `SkillRouter.select()` gains an optional `domain` keyword filter (`manifest.capability.domain == domain`) so a caller who already knows which business domain a task belongs to (e.g. the eventual Marketing agent profile) can disambiguate; callers who omit it keep today's cross-domain relevance-only behavior. A final integration task discovers the *entire* `skillpacks/` tree (Phase 4's `core.weekly-review` plus this phase's five marketing skills) to prove multi-domain coexistence, exercise the new domain filter on a genuine cross-domain collision ("review" appears in both `core.weekly-review` and `marketing.campaign-review`), and prove progressive disclosure still holds at catalog scale (a manifest-only directory with no `SKILL.md` is still discoverable — `discover()` never reads instruction bodies).

**Tech Stack:** Python 3.11, pydantic 2.13, PyYAML 6.0, pytest — same as Phase 4, no new dependencies.

## Global Constraints

- New code/content lives under `skillpacks/marketing/` (repo root) and `backend/tests/agentos/skills/test_marketing_skillpacks.py`. The one exception is `backend/agentos/skills/router.py` and `backend/tests/agentos/skills/test_router.py`, which Task 1 extends with the `domain` parameter — do not touch any other file under `backend/agentos/`.
- **Prerequisite:** this plan assumes Phase 4 (Skill Layer) has already landed — `SkillRegistry`, `SkillRouter`, `SkillInstructionLoader`, and the real `skillpacks/core/weekly-review/` skillpack already exist. If they don't exist yet, land Phase 4 first.
- Every marketing skillpack's `capability.domain` is `"marketing"` (matches the existing `backend/business_core/marketing/` domain naming already used elsewhere in the codebase) and `trust.tier` is `T0` (internal, curated) — same convention as `core.weekly-review`.
- Skill `intents` lists are chosen deliberately to be realistic and mostly non-overlapping across the five marketing skills, so each Task 2–6 test can assert a clean, unambiguous routing result. Task 7's "review" collision test is the one deliberate exception, used specifically to prove why the domain filter exists.
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/<file> -v`.
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.3 (Skill Ecosystem), §23 (MarketingSkills Integration), §44 (Marketing Example), §4 (Phase 5 scope).

---

## File Structure

```text
skillpacks/marketing/
├── market-research/
│   ├── manifest.yaml
│   └── SKILL.md
├── positioning/
│   ├── manifest.yaml
│   └── SKILL.md
├── seo-plan/
│   ├── manifest.yaml
│   └── SKILL.md
├── copywriting/
│   ├── manifest.yaml
│   └── SKILL.md
└── campaign-review/
    ├── manifest.yaml
    └── SKILL.md

backend/agentos/skills/router.py                    # MODIFIED (Task 1)
backend/tests/agentos/skills/test_router.py           # MODIFIED (Task 1)
backend/tests/agentos/skills/test_marketing_skillpacks.py   # NEW (Tasks 2-7)
```

---

### Task 1: `SkillRouter.select()` gains a `domain` filter

**Files:**
- Modify: `backend/agentos/skills/router.py`
- Modify: `backend/tests/agentos/skills/test_router.py`

**Interfaces:**
- Produces (changed): `SkillRouter.select(goal: str, *, allow_business_write: bool = False, domain: str | None = None) -> SkillManifest | None` — when `domain` is given, only skills whose `capability.domain` matches are eligible.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/agentos/skills/test_router.py`, change the `_make_manifest` helper's signature to accept a `domain` keyword (default `"core"`, matching every existing call site so none of Phase 4's tests need to change):

```python
def _make_manifest(
    skill_id: str,
    intents: list[str],
    *,
    tier: TrustTier = TrustTier.T0,
    eval_score: float = 0.8,
    business_write: bool = False,
    domain: str = "core",
) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=" ".join(intents)),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path=skill_id),
        capability=SkillCapability(domain=domain, category="general", intents=intents),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=business_write),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=tier, security_scan="passed"),
        quality=SkillQuality(eval_score=eval_score, success_rate=0.8),
    )
```

Then append these tests to the same file:

```python
def test_router_domain_filter_selects_within_domain():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.weekly-review", ["review"], domain="core"), skill_dir=Path("."))
    registry.register(_make_manifest("marketing.campaign-review", ["review"], domain="marketing"), skill_dir=Path("."))
    router = SkillRouter(registry)

    core_pick = router.select("review", domain="core")
    marketing_pick = router.select("review", domain="marketing")

    assert core_pick is not None and core_pick.metadata.id == "core.weekly-review"
    assert marketing_pick is not None and marketing_pick.metadata.id == "marketing.campaign-review"


def test_router_without_domain_filter_still_returns_a_match():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.weekly-review", ["review"], domain="core"), skill_dir=Path("."))
    router = SkillRouter(registry)

    assert router.select("review") is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_router.py -v`
Expected: FAIL — `SkillRouter.select() got an unexpected keyword argument 'domain'`

- [ ] **Step 3: Modify the implementation**

```python
# backend/agentos/skills/router.py
from __future__ import annotations

import re

from agentos.skills.manifest import SkillLifecycleStatus, SkillManifest, TrustTier
from agentos.skills.registry import SkillRegistry

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_TRUST_WEIGHT: dict[TrustTier, float] = {
    TrustTier.T0: 1.0,
    TrustTier.T1: 0.8,
    TrustTier.T2: 0.5,
    TrustTier.T3: 0.1,
    TrustTier.T4: 0.0,
}


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_skill(goal: str, manifest: SkillManifest) -> float:
    """MVP subset of the blueprint §26 score formula:
    Score = Relevance + Trust + EvalQuality (Cost/Risk/HistoricalSuccess/
    BusinessFit are not tracked yet — later phases add them).
    """
    goal_tokens = _tokenize(goal)
    intent_tokens: set[str] = set()
    for intent in manifest.capability.intents:
        intent_tokens |= _tokenize(intent)
    intent_tokens |= _tokenize(manifest.metadata.description)

    relevance = 0.0
    if goal_tokens and intent_tokens:
        relevance = len(goal_tokens & intent_tokens) / len(goal_tokens)

    trust = _TRUST_WEIGHT.get(manifest.trust.tier, 0.0)
    return relevance * 0.5 + trust * 0.3 + manifest.quality.eval_score * 0.2


class SkillRouter:
    def __init__(self, registry: SkillRegistry, min_trust: TrustTier = TrustTier.T2) -> None:
        self._registry = registry
        self._min_trust = min_trust

    def select(
        self,
        goal: str,
        *,
        allow_business_write: bool = False,
        domain: str | None = None,
    ) -> SkillManifest | None:
        candidates = [
            record.manifest
            for record in self._registry.list(status=SkillLifecycleStatus.ACTIVE)
            if self._is_eligible(record.manifest, allow_business_write=allow_business_write, domain=domain)
        ]
        scored = [(score_skill(goal, manifest), manifest) for manifest in candidates]
        relevant = [(score, manifest) for score, manifest in scored if score > 0]
        if not relevant:
            return None
        relevant.sort(key=lambda pair: pair[0], reverse=True)
        return relevant[0][1]

    def _is_eligible(
        self,
        manifest: SkillManifest,
        *,
        allow_business_write: bool,
        domain: str | None,
    ) -> bool:
        trust_order = list(TrustTier)
        if trust_order.index(manifest.trust.tier) > trust_order.index(self._min_trust):
            return False
        if manifest.permissions.business_write and not allow_business_write:
            return False
        if domain is not None and manifest.capability.domain != domain:
            return False
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_router.py -v`
Expected: 7 passed (5 from Phase 4 + 2 new)

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/router.py backend/tests/agentos/skills/test_router.py
git commit -m "feat(agentos): add domain filter to SkillRouter.select()"
```

---

### Task 2: `marketing.market-research` skillpack

**Files:**
- Create: `skillpacks/marketing/market-research/manifest.yaml`
- Create: `skillpacks/marketing/market-research/SKILL.md`
- Create: `backend/tests/agentos/skills/test_marketing_skillpacks.py`

**Interfaces:** None new — proves one real marketing skill discovers and routes correctly.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agentos/skills/test_marketing_skillpacks.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.loader import SkillManifestError
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter

# backend/tests/agentos/skills/test_marketing_skillpacks.py -> parents[4] is the repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"
MARKETING_SKILLPACKS_ROOT = SKILLPACKS_ROOT / "marketing"


def test_market_research_skill_discovers_and_routes():
    registry = SkillRegistry()
    discovered = registry.discover(MARKETING_SKILLPACKS_ROOT / "market-research")

    assert discovered == ["marketing.market-research"]

    router = SkillRouter(registry)
    selected = router.select("do some market research on our competitors")
    assert selected is not None
    assert selected.metadata.id == "marketing.market-research"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: FAIL — `discovered == []` (directory doesn't exist yet)

- [ ] **Step 3: Create the skillpack**

```yaml
# skillpacks/marketing/market-research/manifest.yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.market-research
  name: Market Research
  version: 1.0.0
  description: Research target market, customer segments, and competitors before a campaign

publisher:
  name: internal
  type: official

source:
  type: local
  path: skillpacks/marketing/market-research

capability:
  domain: marketing
  category: research
  intents:
    - market research
    - understand customers
    - competitive research

runtime:
  entrypoint: SKILL.md
  tools:
    - web.search

permissions:
  filesystem: workspace
  network: read
  business_write: false

risk:
  level: low

trust:
  tier: T0
  security_scan: passed

quality:
  eval_score: 0.85
  success_rate: 0.8
```

```markdown
# skillpacks/marketing/market-research/SKILL.md
# Market Research

Research the target market before planning a campaign:

1. Identify the target customer segments and their pain points.
2. List the top 3-5 competitors and how they position themselves.
3. Summarize market size and growth trends if data is available.
4. Flag any assumptions that still need validation.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add skillpacks/marketing/market-research/manifest.yaml skillpacks/marketing/market-research/SKILL.md backend/tests/agentos/skills/test_marketing_skillpacks.py
git commit -m "feat(skillpacks): add marketing.market-research skillpack"
```

---

### Task 3: `marketing.positioning` skillpack

**Files:**
- Create: `skillpacks/marketing/positioning/manifest.yaml`
- Create: `skillpacks/marketing/positioning/SKILL.md`
- Modify: `backend/tests/agentos/skills/test_marketing_skillpacks.py`

- [ ] **Step 1: Append the failing test**

```python
def test_positioning_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "positioning")
    router = SkillRouter(registry)

    selected = router.select("help me write a positioning statement for our product")

    assert selected is not None
    assert selected.metadata.id == "marketing.positioning"
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: FAIL on `test_positioning_skill_discovers_and_routes` (directory doesn't exist yet); the Task 2 test still passes

- [ ] **Step 3: Create the skillpack**

```yaml
# skillpacks/marketing/positioning/manifest.yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.positioning
  name: Positioning
  version: 1.0.0
  description: Define a clear product positioning and messaging framework

publisher:
  name: internal
  type: official

source:
  type: local
  path: skillpacks/marketing/positioning

capability:
  domain: marketing
  category: positioning
  intents:
    - product positioning
    - positioning statement
    - messaging framework
    - differentiation

runtime:
  entrypoint: SKILL.md
  tools: []

permissions:
  filesystem: workspace
  network: none
  business_write: false

risk:
  level: low

trust:
  tier: T0
  security_scan: passed

quality:
  eval_score: 0.85
  success_rate: 0.8
```

```markdown
# skillpacks/marketing/positioning/SKILL.md
# Positioning

Draft a positioning statement:

1. Name the target customer and the category the product competes in.
2. State the single strongest benefit that matters most to that customer.
3. Name the primary alternative and why this product is a better choice.
4. Compress steps 1-3 into one positioning statement: "For [customer], [product] is the [category] that [benefit], unlike [alternative]."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add skillpacks/marketing/positioning/manifest.yaml skillpacks/marketing/positioning/SKILL.md backend/tests/agentos/skills/test_marketing_skillpacks.py
git commit -m "feat(skillpacks): add marketing.positioning skillpack"
```

---

### Task 4: `marketing.seo-plan` skillpack

**Files:**
- Create: `skillpacks/marketing/seo-plan/manifest.yaml`
- Create: `skillpacks/marketing/seo-plan/SKILL.md`
- Modify: `backend/tests/agentos/skills/test_marketing_skillpacks.py`

- [ ] **Step 1: Append the failing test**

```python
def test_seo_plan_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "seo-plan")
    router = SkillRouter(registry)

    selected = router.select("build an seo keyword plan for our blog")

    assert selected is not None
    assert selected.metadata.id == "marketing.seo-plan"
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: FAIL on `test_seo_plan_skill_discovers_and_routes`; the two previous tests still pass

- [ ] **Step 3: Create the skillpack**

```yaml
# skillpacks/marketing/seo-plan/manifest.yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.seo-plan
  name: SEO Plan
  version: 1.0.0
  description: Build a search engine optimization keyword and content plan

publisher:
  name: internal
  type: official

source:
  type: local
  path: skillpacks/marketing/seo-plan

capability:
  domain: marketing
  category: seo
  intents:
    - seo keyword plan
    - search engine optimization
    - keyword research

runtime:
  entrypoint: SKILL.md
  tools:
    - web.search

permissions:
  filesystem: workspace
  network: read
  business_write: false

risk:
  level: low

trust:
  tier: T0
  security_scan: passed

quality:
  eval_score: 0.85
  success_rate: 0.8
```

```markdown
# skillpacks/marketing/seo-plan/SKILL.md
# SEO Plan

Build a keyword and content plan:

1. List 10-20 candidate keywords relevant to the product and audience.
2. Group keywords by search intent (informational, comparison, transactional).
3. For each group, propose one piece of content that targets it.
4. Note which keywords are highest priority based on relevance to the product, not just volume.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add skillpacks/marketing/seo-plan/manifest.yaml skillpacks/marketing/seo-plan/SKILL.md backend/tests/agentos/skills/test_marketing_skillpacks.py
git commit -m "feat(skillpacks): add marketing.seo-plan skillpack"
```

---

### Task 5: `marketing.copywriting` skillpack

**Files:**
- Create: `skillpacks/marketing/copywriting/manifest.yaml`
- Create: `skillpacks/marketing/copywriting/SKILL.md`
- Modify: `backend/tests/agentos/skills/test_marketing_skillpacks.py`

- [ ] **Step 1: Append the failing test**

```python
def test_copywriting_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "copywriting")
    router = SkillRouter(registry)

    selected = router.select("write ad copy for our landing page")

    assert selected is not None
    assert selected.metadata.id == "marketing.copywriting"
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: FAIL on `test_copywriting_skill_discovers_and_routes`; the three previous tests still pass

- [ ] **Step 3: Create the skillpack**

```yaml
# skillpacks/marketing/copywriting/manifest.yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.copywriting
  name: Copywriting
  version: 1.0.0
  description: Write marketing copy for ads, landing pages, and emails

publisher:
  name: internal
  type: official

source:
  type: local
  path: skillpacks/marketing/copywriting

capability:
  domain: marketing
  category: copywriting
  intents:
    - write ad copy
    - landing page copy
    - marketing copywriting

runtime:
  entrypoint: SKILL.md
  tools: []

permissions:
  filesystem: workspace
  network: none
  business_write: false

risk:
  level: low

trust:
  tier: T0
  security_scan: passed

quality:
  eval_score: 0.85
  success_rate: 0.8
```

```markdown
# skillpacks/marketing/copywriting/SKILL.md
# Copywriting

Write marketing copy:

1. Confirm the single primary action the reader should take.
2. Lead with the benefit that matters most to the target customer, not a feature list.
3. Write 3 headline variants and 1 body paragraph.
4. End with one clear call to action matching the primary action from step 1.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add skillpacks/marketing/copywriting/manifest.yaml skillpacks/marketing/copywriting/SKILL.md backend/tests/agentos/skills/test_marketing_skillpacks.py
git commit -m "feat(skillpacks): add marketing.copywriting skillpack"
```

---

### Task 6: `marketing.campaign-review` skillpack

**Files:**
- Create: `skillpacks/marketing/campaign-review/manifest.yaml`
- Create: `skillpacks/marketing/campaign-review/SKILL.md`
- Modify: `backend/tests/agentos/skills/test_marketing_skillpacks.py`

- [ ] **Step 1: Append the failing test**

```python
def test_campaign_review_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "campaign-review")
    router = SkillRouter(registry)

    selected = router.select("review how our last campaign performed")

    assert selected is not None
    assert selected.metadata.id == "marketing.campaign-review"
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: FAIL on `test_campaign_review_skill_discovers_and_routes`; the four previous tests still pass

- [ ] **Step 3: Create the skillpack**

```yaml
# skillpacks/marketing/campaign-review/manifest.yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.campaign-review
  name: Campaign Review
  version: 1.0.0
  description: Review a completed marketing campaign's performance against its goals

publisher:
  name: internal
  type: official

source:
  type: local
  path: skillpacks/marketing/campaign-review

capability:
  domain: marketing
  category: analytics
  intents:
    - review campaign performance
    - campaign retrospective
    - marketing analytics review

runtime:
  entrypoint: SKILL.md
  tools:
    - analytics.read

permissions:
  filesystem: workspace
  network: none
  business_write: false

risk:
  level: low

trust:
  tier: T0
  security_scan: passed

quality:
  eval_score: 0.85
  success_rate: 0.8
```

```markdown
# skillpacks/marketing/campaign-review/SKILL.md
# Campaign Review

Review a completed campaign:

1. Restate the campaign's original goal and target metric.
2. Report the actual metric achieved versus the target.
3. Identify what worked and what didn't, with evidence, not guesses.
4. Recommend one specific change to try in the next campaign.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add skillpacks/marketing/campaign-review/manifest.yaml skillpacks/marketing/campaign-review/SKILL.md backend/tests/agentos/skills/test_marketing_skillpacks.py
git commit -m "feat(skillpacks): add marketing.campaign-review skillpack"
```

---

### Task 7: Full-catalog integration — multi-domain coexistence, domain-filter disambiguation, progressive disclosure at scale

**Files:**
- Modify: `backend/tests/agentos/skills/test_marketing_skillpacks.py`

**Interfaces:** None new — this task only adds tests proving the catalog-wide behavior of Tasks 1–6 combined with Phase 4's `core.weekly-review`.

- [ ] **Step 1: Append the failing tests**

```python
def test_full_catalog_discovers_all_core_and_marketing_skills():
    registry = SkillRegistry()
    discovered = registry.discover(SKILLPACKS_ROOT)

    assert set(discovered) >= {
        "core.weekly-review",
        "marketing.market-research",
        "marketing.positioning",
        "marketing.seo-plan",
        "marketing.copywriting",
        "marketing.campaign-review",
    }


def test_domain_filter_disambiguates_review_skills_across_domains():
    registry = SkillRegistry()
    registry.discover(SKILLPACKS_ROOT)
    router = SkillRouter(registry)

    core_pick = router.select("review", domain="core")
    marketing_pick = router.select("review", domain="marketing")

    assert core_pick is not None and core_pick.metadata.id == "core.weekly-review"
    assert marketing_pick is not None and marketing_pick.metadata.id == "marketing.campaign-review"


def test_discover_never_reads_skill_md_bodies(tmp_path: Path):
    manifest_only_dir = tmp_path / "manifest-only-skill"
    manifest_only_dir.mkdir()
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": "test.manifest-only", "name": "x", "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(manifest_only_dir)},
        "capability": {"domain": "core", "category": "test", "intents": ["x"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.5, "success_rate": 0.5},
    }
    (manifest_only_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    # deliberately no SKILL.md written

    registry = SkillRegistry()
    discovered = registry.discover(tmp_path)

    assert discovered == ["test.manifest-only"]

    loader = SkillInstructionLoader(registry)
    with pytest.raises(SkillManifestError):
        loader.load("test.manifest-only")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_marketing_skillpacks.py -v`
Expected: PASS if Tasks 1–6 landed correctly in this session already (they should — these are pure integration checks over content already committed); if any of Tasks 2–6's skillpacks is missing, `test_full_catalog_discovers_all_core_and_marketing_skills` fails with a clear `set` mismatch telling you which one

- [ ] **Step 3: Run the full `agentos` skills suite to confirm everything holds together**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/ -v`
Expected: all passing — Phase 4's 20 tests (with `test_router.py` now at 7 instead of 5, so 22) + this phase's 8 `test_marketing_skillpacks.py` tests (5 per-skill + 3 catalog-wide) = 30 total

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agentos/skills/test_marketing_skillpacks.py
git commit -m "test(agentos): add full marketing skillpack catalog integration tests"
```

---

## Verification (end of Phase 5)

1. Run the full skills suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/ -v` — all tests pass (30 total per Task 7 Step 3).
2. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — no regressions in Phase 0/1/3/4 tests.
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Manually read all five `skillpacks/marketing/*/SKILL.md` files and confirm each gives concrete, actionable steps rather than vague guidance — these are the actual instructions an agent will follow once wired up.

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 6 (External Skill Supply Chain — DISCOVER→FETCH→PIN VERSION→...→PROMOTE, `awesome-agent-skills` as a discovery source, trust tiers T1-T4 actually exercised for non-internal skills) is next. It should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed. Wiring an actual Marketing agent profile to call `SkillRouter.select(goal, domain="marketing")` — so these skills are reachable from a real `AgentRuntime.run()` — is also deferred; it depends on Phase 1's `runtime.py`/`executor.py` gaining a skill-instruction injection point, which hasn't been scoped yet.
