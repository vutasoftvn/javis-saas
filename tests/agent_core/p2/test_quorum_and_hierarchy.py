from __future__ import annotations

from agent_core.governance.quorum import (
    RoleHierarchyTree,
    WeightedApprover,
    WeightedQuorumPolicy,
)


def test_role_hierarchy_and_weighted_quorum():
    """Kiểm thử Role Hierarchy và Weighted Quorum Policy."""
    # 1. Role Hierarchy Tree
    tree = RoleHierarchyTree()
    tree.add_relation("finance_lead", "finance_director")
    tree.add_relation("finance_director", "chief_financial_officer")

    assert tree.is_superior_or_equal("chief_financial_officer", "finance_lead") is True
    assert tree.is_superior_or_equal("finance_director", "finance_lead") is True
    assert tree.is_superior_or_equal("finance_lead", "chief_financial_officer") is False
    assert tree.is_superior_or_equal("admin", "chief_financial_officer") is True

    # 2. Weighted Quorum Policy
    # Cần 5 điểm: CFO (weight 4), VP (weight 3), Lead (weight 2)
    policy = WeightedQuorumPolicy(
        required_weight=5,
        approvers=(
            WeightedApprover(principal_or_role="cfo", weight=4),
            WeightedApprover(principal_or_role="vp_operations", weight=3),
            WeightedApprover(principal_or_role="finance_lead", weight=2),
        ),
    )

    # CFO + VP = 4 + 3 = 7 >= 5 -> Đạt
    assert policy.evaluate_decisions({"cfo", "vp_operations"}) is True

    # CFO + Lead = 4 + 2 = 6 >= 5 -> Đạt
    assert policy.evaluate_decisions({"cfo", "finance_lead"}) is True

    # Chỉ VP = 3 < 5 -> Chưa đạt
    assert policy.evaluate_decisions({"vp_operations"}) is False
