# ADR-FIN-006: TT58 Mode 1 ships first
## Status
Accepted (2026-08-13)
## Context
Four modes exist, but only Mode 1 has validated templates in this release.
## Decision
Declare all modes and reject activation of Modes 2-4 with a clear error.
## Consequences
Unsupported modes cannot produce plausible but incorrect books.
