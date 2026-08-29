from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec


def _spec(cap_id: str) -> CapabilitySpec:
    return CapabilitySpec(id=cap_id, input_schema={}, output_schema={})


def test_get_handler_returns_registered_handler():
    reg = CapabilityRegistry()

    async def handler(payload, ctx):
        return {"ok": True}

    reg.register(_spec("engagement.thread.read"), handler)
    assert reg.get_handler("engagement.thread.read") is handler


def test_get_handler_returns_none_for_unknown_capability():
    reg = CapabilityRegistry()
    assert reg.get_handler("does.not.exist") is None
