"""End-to-End Simulation Test for Full 14-Member Executive Boardroom Deliberation.

Simulates a high-stakes strategic boardroom debate across all 14 C-Level roles:
- CoS (Chief of Staff)
- CEO, CTO, CFO
- CPO, CMO, CRO, CCO
- COO, VPE, CHRO
- CISO, GC, CDO, CAIO

Verifies:
1. Independent drafting outputs from diverse roles
2. Synthesis into BoardroomMemo
3. Extraction and preservation of verbatim Dissent (Preserved Dissent)
4. Enforcing Binding Criteria with 12WY Checkpoint Week
5. Evidence tagging reflecting Startup OS Snapshot freshness
"""

from __future__ import annotations

import pytest

from agent.executive_board.analyzers import (
    calculate_deliberation_consensus_index,
    score_meeting_actionability,
)
from agent.executive_board.models import (
    BindingCriteria,
    BoardroomMemo,
    ExecutiveAnalysisOutcome,
)
from agent.executive_board.runner import ExecutiveBoardRunner


def test_full_14_member_boardroom_simulation():
    # Strategic Question: "Should we pivot our pricing to Enterprise Usage-Based and open a US sales branch in Cycle 2 (Weeks 13-24)?"
    deliberation_id = "delib-14-csuite-001"
    question = "Should we expand to US Enterprise market with usage-based pricing in Cycle 2?"

    # 1. Simulate 14 independent outcomes (Phase 2 Independent Drafting)
    # The proposal on the table:
    # Option 1: "US Enterprise Expansion with Usage-Based Pricing" (Favored by CEO, CRO, CMO, COO)
    # Option 2: "Consolidate Domestic Base & Perfect Product Moat" (Favored by CFO, CISO, GC, CPO, CCO)
    # Option 3: "Global Self-Serve Developer First" (Favored by CTO, VPE, CAIO, CDO, CHRO)

    roles_votes = {
        "ceo": ("Option 1: US Enterprise Expansion", "Go big or go home, 144-week vision requires US market"),
        "cro": ("Option 1: US Enterprise Expansion", "Pipeline velocity will double with enterprise ACV"),
        "cmo": ("Option 1: US Enterprise Expansion", "Brand positioning will gain massive prestige in US"),
        "coo": ("Option 1: US Enterprise Expansion", "12WY operational rhythm can support international branch"),
        "cfo": ("Option 2: Consolidate Domestic Base", "Runway is only 20 weeks; US expansion burns too much cash"),
        "ciso": ("Option 2: Consolidate Domestic Base", "US enterprise requires SOC2 Type II compliance not yet ready"),
        "gc": ("Option 2: Consolidate Domestic Base", "US legal entity and employment regulations require 12 weeks setup"),
        "cpo": ("Option 2: Consolidate Domestic Base", "Usage-based billing UI/UX is not validated; risk of customer churn"),
        "cco": ("Option 2: Consolidate Domestic Base", "Domestic NRR is 115%; we must not abandon existing accounts"),
        "cto": ("Option 3: Global Self-Serve Developer First", "Architecture is cloud-native, developer self-serve has 10x lower TCO"),
        "vpe": ("Option 3: Global Self-Serve Developer First", "Dev self-serve keeps DORA lead time under 12 hours"),
        "caio": ("Option 3: Global Self-Serve Developer First", "Developer APIs allow automated agent ingestion with lower token cost"),
        "cdo": ("Option 3: Global Self-Serve Developer First", "Self-serve generates cleaner event stream data for training"),
        "chro": ("Option 3: Global Self-Serve Developer First", "Hiring US sales reps costs $250k/head; developer model scales without hiring blitz"),
    }

    outcomes = []
    for role_key, (voted_opt, reason) in roles_votes.items():
        outcomes.append(
            ExecutiveAnalysisOutcome(
                kind="executive.analysis.completed.v1",
                deliberation_id=deliberation_id,
                frame_version=1,
                role_key=role_key,
                descriptor={
                    "conclusion": voted_opt,
                    "options": [{"title": voted_opt, "trade_off": reason}],
                    "risks_and_unknowns": [f"Unresolved concern from {role_key.upper()}: {reason}"],
                    "confidence": 0.85,
                },
                context_snapshot_age_weeks=2,
                evidence_tag="🟢 Fresh Snapshot (W2)",
            )
        )

    # CoS synthesizes deliberation:
    # Top vote getter is Option 2 (5 votes) vs Option 3 (5 votes) vs Option 1 (4 votes).
    # Suppose Founder leans towards "Option 2: Consolidate Domestic Base"
    favored_option = "Option 2: Consolidate Domestic Base"

    memo: BoardroomMemo = ExecutiveBoardRunner.synthesize_boardroom_deliberation(
        deliberation_id=deliberation_id,
        question=question,
        outcomes=outcomes,
        favored_option=favored_option,
        context_snapshot_age_weeks=2,
        binding_criteria=BindingCriteria(
            success_criteria=[
                "Domestic ARR reaches $1M by Week 24",
                "NRR maintained above 115%",
                "Complete SOC2 Type II audit readiness",
            ],
            kill_criteria=[
                "If Domestic ARR growth < 10% by Week 6",
                "If Runway drops below 16 weeks without revenue boost",
            ],
            review_checkpoint_week=6,
        ),
    )

    # Verify Boardroom Memo Structure
    assert memo.deliberation_id == deliberation_id
    assert memo.recommended_option == favored_option
    assert len(memo.vote_tally) == 14

    # Check vote distribution
    assert memo.vote_tally["cfo"] == "Option 2: Consolidate Domestic Base"
    assert memo.vote_tally["ceo"] == "Option 1: US Enterprise Expansion"
    assert memo.vote_tally["cto"] == "Option 3: Global Self-Serve Developer First"

    # Verify Preserved Dissent:
    # 5 roles voted for Option 2 (CFO, CISO, GC, CPO, CCO)
    # The other 9 roles (CEO, CRO, CMO, COO, CTO, VPE, CAIO, CDO, CHRO) must have their dissent preserved!
    assert len(memo.preserved_dissent) == 9
    dissenting_roles = {d.role_key for d in memo.preserved_dissent}
    assert "ceo" in dissenting_roles
    assert "cto" in dissenting_roles
    assert "cro" in dissenting_roles
    assert "cfo" not in dissenting_roles  # CFO agreed with favored option

    # Verify Dissent Content Preservation
    ceo_dissent = next(d for d in memo.preserved_dissent if d.role_key == "ceo")
    assert ceo_dissent.recommended_alternative == "Option 1: US Enterprise Expansion"
    assert "144-week vision" in ceo_dissent.unresolved_concern

    # Verify Binding Criteria & Checkpoint
    assert memo.binding_criteria is not None
    assert memo.binding_criteria.review_checkpoint_week == 6
    assert len(memo.binding_criteria.kill_criteria) == 2

    # Verify Evidence Tag & Freshness
    assert "Fresh Snapshot (W2)" in memo.evidence_tag

    # Test CoS Analyzers
    consensus_idx = calculate_deliberation_consensus_index(memo.vote_tally)
    # Max votes is 5 out of 14 -> ~0.36
    assert 0.35 <= consensus_idx <= 0.37

    actionability = score_meeting_actionability(
        dissent_count=len(memo.preserved_dissent),
        binding_criteria_present=True,
    )
    assert actionability == 10.0  # High quality, rigorous deliberation with binding criteria
