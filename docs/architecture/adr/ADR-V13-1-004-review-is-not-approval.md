# ADR-V13-1-004: Review and Approval are distinct and compose
## Status
Accepted (2026-08-13)
## Context
Three domain-specific approval tables already exist (`WorkflowApproval`, `PendingApproval`, `EmailApproval`). The spec's review/rework loop looks superficially similar and invites merging them into one generic approval engine.
## Decision
Add a separate `work_reviews` table. Review answers "is this output good enough"; Approval answers "may this risky action proceed". Do not build a generic `Approval` or `PolicyEngine`. The two compose only at the Needs You read layer.
## Consequences
No migration of the three existing approval tables, so no existing approval flow changes. Rework counting and the reviewer contract live only on the Review side; the human-approval gate on outbound/risky actions is untouched.
