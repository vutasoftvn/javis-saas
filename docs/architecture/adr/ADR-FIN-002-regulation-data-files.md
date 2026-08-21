# ADR-FIN-002: Regulation content is data
## Status
Accepted (2026-08-13)
## Context
TT58 templates change independently of application logic.
## Decision
Store regulation metadata and modes under `backend/regulations/vn/tt58_2026`.
## Consequences
Python and Dart do not hard-code statutory forms.
