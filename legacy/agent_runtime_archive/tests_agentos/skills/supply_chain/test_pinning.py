import pytest

from agentos.skills.supply_chain.pinning import UnpinnedSkillSourceError, require_pinned_commit


def test_require_pinned_commit_accepts_a_real_sha():
    commit = require_pinned_commit("community.faq-writer", "4bc9a82c1234567890abcdef1234567890abcdef")
    assert commit == "4bc9a82c1234567890abcdef1234567890abcdef"


def test_require_pinned_commit_rejects_missing_commit():
    with pytest.raises(UnpinnedSkillSourceError):
        require_pinned_commit("community.faq-writer", None)


def test_require_pinned_commit_rejects_branch_name():
    with pytest.raises(UnpinnedSkillSourceError):
        require_pinned_commit("community.faq-writer", "main")
