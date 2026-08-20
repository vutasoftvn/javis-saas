#!/usr/bin/env python3
"""Verify projection parity between legacy and canonical COSA data stores.

Historical note: this script previously printed hardcoded row counts and a
fake "MATCHED" hash comparison without ever touching a database (comment in
the old version admitted: "Gia lap query DB" — "simulate DB query").
docs/architecture/COSA_PHASE8_RETIREMENT_COMPLETION.md cited that fabricated
output as evidence of "100% projection parity".

No real dual-store (legacy vs. canonical) data set currently exists to
compare: per docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md's
"Persistence-model retirement guard", AgentRun/Artifact persistence was
MOVED to agent_runtime.*, not duplicated — workforce/* modules re-export the
same tables. Until a genuine dual-write migration exists with two real
tables to compare, this script must fail loudly instead of fabricating a
"passed" result that architecture docs can cite as evidence.
"""
import sys


class ProjectionParityNotImplementedError(Exception):
    pass


def verify_parity() -> None:
    raise ProjectionParityNotImplementedError(
        "verify_projection_parity is NOT IMPLEMENTED. There is currently no "
        "real dual-store (legacy vs. canonical) data set to compare against "
        "-- do not cite this script as evidence of projection parity in any "
        "architecture document until it is implemented against real tables."
    )


def main() -> int:
    try:
        verify_parity()
        return 0
    except ProjectionParityNotImplementedError as exc:
        print(f"NOT IMPLEMENTED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
