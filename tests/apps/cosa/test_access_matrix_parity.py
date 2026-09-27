"""Parity spec agent ↔ registry ↔ access matrix ↔ AGENT_CAP của company
(spec 2026-09-27-chat-business-actions §4.3). Lệch pha trước đây chỉ lộ ở runtime
(401 vì endpoint không khai báo agentCapabilities, 404 vì trỏ endpoint không tồn tại)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from apps.cosa.agents import catalog
from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES, MATRIX, Tier

REPO = Path(__file__).resolve().parents[3]
COMPANY = REPO / "services/company"
AGENT_CAP_FILE = COMPANY / "shared/auth/agent-capabilities.ts"
# Capability đăng ký động ngoài register_cosa_capabilities (plane tự đăng ký).
DYNAMIC_REFS = {"agent.consult", "memory.fact.propose"}
CHAT_PROFILES = {"operations", "founder_assistant"}


def _agent_cap_entries() -> dict[str, str]:
    text = AGENT_CAP_FILE.read_text(encoding="utf-8")
    return dict(re.findall(r"^\s+([A-Z_0-9]+):\s*\"([a-z_.0-9]+)\"", text, flags=re.M))


def _agent_refs() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for entry in catalog._RAW_ENTRIES:
        for cap in entry.agent_spec.capability_refs or []:
            refs.setdefault(cap, set()).add(entry.profile_key)
    return refs


def _company_sources() -> str:
    parts: list[str] = []
    for root, dirs, files in os.walk(COMPANY):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "encore.gen", "tests", ".encore")]
        for name in files:
            if not name.endswith(".ts"):
                continue
            path = Path(root) / name
            if path == AGENT_CAP_FILE:
                continue
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_every_agent_ref_is_registered_and_in_matrix(registered_capability_ids: set[str]) -> None:
    refs = _agent_refs()
    missing_registry = sorted(set(refs) - registered_capability_ids - DYNAMIC_REFS)
    assert not missing_registry, f"agent refs chưa đăng ký: {missing_registry}"
    missing_matrix = sorted(set(refs) - set(MATRIX))
    assert not missing_matrix, f"agent refs thiếu trong access matrix: {missing_matrix}"


def test_every_registered_capability_is_in_matrix(registered_capability_ids: set[str]) -> None:
    # Capability MCP (sandbox/connector) có tiền tố riêng, bậc do manifest quyết định.
    unknown = sorted(
        c for c in registered_capability_ids - set(MATRIX) if not c.startswith(("sandbox.", "mcp."))
    )
    assert not unknown, f"capability đăng ký nhưng chưa xếp bậc trong access matrix: {unknown}"


def test_company_agent_cap_matches_matrix() -> None:
    company = set(_agent_cap_entries().values())
    for cap, entry in MATRIX.items():
        if entry.company_agent_cap:
            assert entry.company_agent_cap in company, (
                f"{cap}: AGENT_CAP {entry.company_agent_cap!r} thiếu ở agent-capabilities.ts"
            )
    declared = {e.company_agent_cap for e in MATRIX.values() if e.company_agent_cap}
    orphan = sorted(company - declared)
    assert not orphan, f"AGENT_CAP không có trong access matrix: {orphan}"


def test_every_agent_cap_is_used_by_a_company_endpoint() -> None:
    src = _company_sources()
    unused = sorted(k for k in _agent_cap_entries() if f"AGENT_CAP.{k}" not in src)
    assert not unused, f"AGENT_CAP khai báo nhưng không endpoint nào dùng: {unused}"


def test_tier_policy_for_chat_profiles() -> None:
    for cap, profiles in _agent_refs().items():
        if not profiles & CHAT_PROFILES:
            continue
        entry = MATRIX[cap]
        assert entry.tier is not Tier.T3_EXTERNAL, f"{cap} (T3) không được vào spec chat"
        if entry.tier is Tier.T2_COMMIT:
            assert cap in CHAT_T2_CAPABILITIES, f"{cap} (T2) phải buộc duyệt trong chat"
    assert all(MATRIX[cap].tier is Tier.T2_COMMIT for cap in CHAT_T2_CAPABILITIES)
    assert "engagement.message.send" not in CHAT_T2_CAPABILITIES
