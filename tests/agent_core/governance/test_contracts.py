from __future__ import annotations

from agent_core.governance.contracts import PinnedSpecIdentity, SpecResolutionManifest


def _identity(spec_id: str = "cofounder", version: str = "1") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(
        spec_kind="agent",
        spec_id=spec_id,
        spec_version=version,
        definition_hash="a" * 64,
    )


def test_pinned_spec_identity_holds_the_four_required_fields():
    identity = _identity()

    assert identity.spec_kind == "agent"
    assert identity.spec_id == "cofounder"
    assert identity.spec_version == "1"
    assert identity.definition_hash == "a" * 64


def test_spec_resolution_manifest_starts_empty():
    manifest = SpecResolutionManifest()

    assert manifest.entries == ()


def test_with_entry_appends_a_new_pinned_identity():
    manifest = SpecResolutionManifest()
    entry = _identity()

    updated = manifest.with_entry(entry)

    assert updated.entries == (entry,)
    assert manifest.entries == ()  # bản gốc không bị mutate


def test_with_entry_never_drops_an_earlier_entry():
    first = _identity(spec_id="supervisor")
    second = _identity(spec_id="legal")  # vd: delegate động, resolve giữa chừng Run

    manifest = SpecResolutionManifest().with_entry(first).with_entry(second)

    assert manifest.entries == (first, second)


def test_with_entry_is_idempotent_for_the_same_identity():
    entry = _identity()
    manifest = SpecResolutionManifest().with_entry(entry)

    manifest_again = manifest.with_entry(entry)

    assert manifest_again.entries == (entry,)
