from __future__ import annotations

from agent.contracts.prompt import PromptSpec
from agent.governance.contracts import PinnedSpecIdentity


def test_prompt_spec_has_sensible_defaults():
    spec = PromptSpec(id="cofounder/system")

    assert spec.version == "1.0.0"
    assert spec.text == ""
    assert spec.variables == []
    assert spec.definition_hash is None


def test_prompt_spec_compute_hash_is_deterministic():
    a = PromptSpec(id="cofounder/system", text="Bạn là trợ lý.")
    b = PromptSpec(id="cofounder/system", text="Bạn là trợ lý.")

    assert a.compute_hash() == b.compute_hash()


def test_prompt_spec_compute_hash_changes_with_text():
    a = PromptSpec(id="cofounder/system", text="Bản A")
    b = PromptSpec(id="cofounder/system", text="Bản B")

    assert a.compute_hash() != b.compute_hash()


def test_prompt_spec_with_hash_returns_a_copy_with_definition_hash_set():
    spec = PromptSpec(id="cofounder/system", text="Nội dung")

    pinned = spec.with_hash()

    assert spec.definition_hash is None
    assert pinned.definition_hash == spec.compute_hash()


def test_prompt_spec_to_pinned_identity_uses_prompt_kind():
    spec = PromptSpec(id="cofounder/system", version="2026.08.3", text="Nội dung").with_hash()

    identity = spec.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="prompt",
        spec_id="cofounder/system",
        spec_version="2026.08.3",
        definition_hash=spec.definition_hash,
    )
