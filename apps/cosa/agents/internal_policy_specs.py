"""Spec nội bộ cho phép cấu hình model-policy nhưng KHÔNG phải profile công khai.

Không thêm vào AGENT_PROFILE_SPECS/OWNER_AGENT_PROFILES (xem quyết định Dự án B).
Module nhẹ (chỉ phụ thuộc `specs.py`) để `model_policy_routes.py` import được
mà không kéo import chain nặng."""

from __future__ import annotations

from agent.contracts.spec import AgentSpec

from apps.cosa.agents.specs import COSA_VERIFIER_AGENT_SPEC

__all__ = ["INTERNAL_MODEL_POLICY_SPECS"]

INTERNAL_MODEL_POLICY_SPECS: dict[str, AgentSpec] = {"verifier": COSA_VERIFIER_AGENT_SPEC}
