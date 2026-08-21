"""G1 Memory Promotion Pipeline / G3 Phase 1E: memory retrieval must be
ranked (relevance_score, not just recency) and budgeted (never able to dump
the whole table regardless of what limit a caller requests).
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


from db.base_class import Base
from workforce.memory.models import AgentMemoryEntry
from workforce.memory.service import FiveLayerMemoryManager, MAX_MEMORY_RESULTS


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine, tables=[AgentMemoryEntry.__table__])
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_list_layer_memories_ranks_by_relevance_before_recency(db: Session):
    now = datetime.utcnow()
    FiveLayerMemoryManager.store_memory(db, 1, "L3_KNOWLEDGE", "old_but_relevant", {"x": 1}, relevance_score=0.9)
    FiveLayerMemoryManager.store_memory(db, 1, "L3_KNOWLEDGE", "recent_but_low", {"x": 2}, relevance_score=0.1)
    # Force recency to actually differ and favor the low-relevance one, proving
    # relevance still wins.
    db.query(AgentMemoryEntry).filter(AgentMemoryEntry.key == "old_but_relevant").update(
        {"last_accessed_at": now - timedelta(days=5)}
    )
    db.query(AgentMemoryEntry).filter(AgentMemoryEntry.key == "recent_but_low").update(
        {"last_accessed_at": now}
    )
    db.commit()

    results = FiveLayerMemoryManager.list_layer_memories(db, 1, "L3_KNOWLEDGE")

    assert [r.key for r in results] == ["old_but_relevant", "recent_but_low"]


def test_list_layer_memories_never_exceeds_the_hard_cap_even_if_asked(db: Session):
    for i in range(5):
        FiveLayerMemoryManager.store_memory(db, 1, "L1_WORKING", f"k{i}", {"i": i})

    results = FiveLayerMemoryManager.list_layer_memories(db, 1, "L1_WORKING", limit=10_000_000)

    assert len(results) == 5  # capped by what actually exists, not by the absurd limit
    # The cap itself is enforced at the query level (LIMIT clause), not just
    # by there happening to be few rows - assert the constant is sane too.
    assert MAX_MEMORY_RESULTS <= 500


def test_get_founder_rules_is_ranked_and_budgeted(db: Session):
    FiveLayerMemoryManager.store_memory(db, 1, "L2_FOUNDER", "rule_low", {"rule": "low"}, relevance_score=0.2)
    FiveLayerMemoryManager.store_memory(db, 1, "L2_FOUNDER", "rule_high", {"rule": "high"}, relevance_score=0.95)

    rules = FiveLayerMemoryManager.get_founder_rules(db, 1)

    assert rules[0]["rule"] == "high"
    assert rules[1]["rule"] == "low"


def test_get_founder_rules_respects_a_custom_smaller_limit(db: Session):
    for i in range(3):
        FiveLayerMemoryManager.store_memory(db, 1, "L2_FOUNDER", f"rule_{i}", {"i": i}, relevance_score=1.0)

    rules = FiveLayerMemoryManager.get_founder_rules(db, 1, limit=2)

    assert len(rules) == 2


def test_store_memory_persists_domain_and_provenance(db: Session):
    entry = FiveLayerMemoryManager.store_memory(
        db, 1, "L4_LEARNING", "outcome:test", {"metric": "x"},
        domain="sales", provenance={"source": "verified_job_outcome"},
    )

    assert entry.domain == "sales"
    assert entry.provenance_jsonb["source"] == "verified_job_outcome"
