# ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE: Production Release Gate & Governance for Customer Engagement Autopilot

- **Status:** APPROVED (Fail-Closed Default)
- **Date:** 2026-08-28
- **Context:** Customer Support Autopilot Phase 4 (`engagement.*` write mode)

---

## 1. Context and Problem Statement

Customer Support Autopilot introduces autonomous action execution in customer messaging:
- Sending customer messages (`engagement.message.send`)
- Routing and re-assigning customer threads (`engagement.assignment.write`)

Direct write actions carry operational and legal risks if released without strict staging verification, quality thresholds, and fail-safe human override controls.

---

## 2. Decision

1. **Environment Gating (Fail-Closed)**:
   - By default, Autopilot write mode is enabled ONLY for `["test", "staging"]` environments.
   - Any attempt to enable Autopilot on `production` is blocked in `AutopilotSettingsService` with `APIError.failedPrecondition`, unless the explicit production gate override flag `ENGAGEMENT_AUTOPILOT_PROD_GATE_OVERRIDE=true` is present alongside signed approval.

2. **Pre-Authorized Template Boundary**:
   - Autopilot can directly send responses without human-in-the-loop ONLY when matching a pre-authorized FAQ template with registered `template_ref`.
   - Free-form LLM generation always enters `RunStatus.WAITING_APPROVAL` with durable checkpoints.

3. **Multi-Layer Kill Switch**:
   - **Operator Kill Switch**: Instant toggle via API (`POST /commercial/engagement/autopilot/kill-switch`) or DB `engagement_autopilot_settings.enabled = false`.
   - **Automatic Threshold Monitor**: Automatically trips the kill switch if error rate > 5%, human takeover > 15%, or containment rate < 80% over rolling runs.
   - **Worker Pre-Flight Check**: Worker halts run execution immediately (`run.cancelled`) if the trigger rule is disabled before starting or before resuming.

4. **Human Drift Guard**:
   - When an approval resumes, if the customer thread has been claimed by a human desk agent (`activeMode == "human_assigned"`), the automated send is cancelled immediately.

---

## 3. Verification & Compliance Checklist

- [x] Pre-authorized template matching with zero hallucination.
- [x] Durable approval pause & resume with cryptographic binding.
- [x] Human takeover drift cancellation.
- [x] 100% passing write-mode eval suite (5 canonical test cases).
- [x] End-to-end correlation and audit trail from event intake to delivery.
