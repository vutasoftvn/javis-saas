"""Unit tests for AI Program Registry and boundary rules."""

import pytest
from app.ai.programs.registry import AIProgramRegistry, ProgramRegistration
from app.ai.programs.base import BaseCOSAProgram


class DummyProgram(BaseCOSAProgram):
    program_key = "dummy.test"
    def forward(self, **kwargs):
        return {"test": True}


def test_registry_initializes_defaults():
    """Verify approved programs are registered by default."""
    AIProgramRegistry.initialize_default_programs()
    assert AIProgramRegistry.exists("ceo.brief")
    assert AIProgramRegistry.exists("sales.lead_qualification")
    
    programs = AIProgramRegistry.list_programs()
    keys = [p.key for p in programs]
    assert "ceo.brief" in keys
    assert "sales.lead_qualification" in keys


def test_registry_rejects_forbidden_strategy_programs():
    """Verify V13 Focused Company Cycle boundary rules: PESTEL/SWOT/TOWS/BSC/Strategy cannot be registered."""
    forbidden_keys = [
        "strategy.pestel",
        "strategy.swot",
        "strategy.tows",
        "strategy.bsc",
        "strategy.portfolio.matrix",
        "pestel.analysis",
        "swot.matrix",
        "tows.strategic_options",
        "bsc.scorecard",
        "portfolio_strategy.canvas",
    ]

    for key in forbidden_keys:
        meta = ProgramRegistration(
            key=key,
            name="Forbidden",
            domain="strategy",
            description="Forbidden",
            program_class_path="dummy",
        )
        with pytest.raises(ValueError) as exc_info:
            AIProgramRegistry.register(key=key, program_cls=DummyProgram, meta=meta)
        assert "is forbidden under V13 Focused Company Cycle OS" in str(exc_info.value)
