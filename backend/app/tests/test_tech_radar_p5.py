"""Test suite for Technology Radar in P5 (Spec §104)."""

from unittest.mock import MagicMock
from app.modules.tech_radar.models import TechnologyRadarItem
from app.modules.tech_radar.service import TechRadarService


def test_tech_radar_seed_defaults():
    """Test seeding standard technology radar items from Spec §104."""
    mock_db = MagicMock()
    # Simulate empty DB initially
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()

    seeded = TechRadarService.seed_defaults(mock_db, workspace_id=1)
    assert len(seeded) >= 8

    # Verify key technologies are included
    names = [s.name for s in seeded]
    assert "PostgreSQL LISTEN/NOTIFY" in names
    assert "DSPy" in names
    assert "LiteLLM" in names
    assert "Docker Sandbox" in names
    assert "AgentSkeptic" in names
    assert "n8n Workflow Engine" in names


def test_tech_radar_update_item():
    """Test updating technology radar ring status and maturity."""
    mock_db = MagicMock()
    item = TechnologyRadarItem(
        id=12345,
        workspace_id=1,
        name="Mem0 / Zep",
        category="Memory",
        status="ASSESS",
        maturity="beta",
        potential="medium",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = item

    updated = TechRadarService.update_item(
        mock_db,
        item_id=12345,
        status="TRIAL",
        potential="high",
        cosa_use="pattern",
    )
    assert updated.status == "TRIAL"
    assert updated.potential == "high"
    assert updated.cosa_use == "pattern"
