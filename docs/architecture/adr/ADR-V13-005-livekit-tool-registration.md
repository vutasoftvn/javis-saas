# ADR-V13-005: LiveKit changes are additive tool registration
## Status
Accepted (2026-08-13)
## Context
LiveKit session, transport, and barge-in infrastructure already exists.
## Decision
Register domain tools in `app/core/tool_registry.py` and filter them by workspace flags.
## Consequences
Voice gains V13 read tools without changing the realtime transport boundary.
