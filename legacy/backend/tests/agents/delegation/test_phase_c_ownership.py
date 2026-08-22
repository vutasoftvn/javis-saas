from pathlib import Path


def test_phase_c_canonical_owners_are_documented():
    root = Path(__file__).resolve().parents[4]
    text = (root / "docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md").read_text()

    assert "TaskBoardService" in text
    assert "LongRunningWorkProviderManager" in text
    assert "DelegationProviderManager" in text
