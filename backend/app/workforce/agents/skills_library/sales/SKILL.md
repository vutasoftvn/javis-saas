---
name: sales_lead_qualification
domain: sales
description: Domain skill for B2B lead qualification, MEDDPICC scoring, and objection handling.
required_context:
  - icp_criteria
  - pricing_tier
  - decision_maker_role
tool_permissions:
  - sales.lead_score
  - sales.pipeline_update
---

# Sales Lead Qualification Skill

## Objective
Qualify inbound leads, assess pipeline velocity, and recommend next-best sales actions.

## Execution Guidelines
1. Verify budget, authority, need, and timeline (BANT/MEDDPICC).
2. Document objections and key decision criteria.
3. Propose follow-up sequence.
