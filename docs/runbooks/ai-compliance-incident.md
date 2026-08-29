# Runbook: AI Compliance Incident Response

## 1. Trigger Conditions & Severity Levels
- **CRITICAL**: Prohibited domain automated action, data breach to unapproved provider, or immediate legal order.
- **HIGH**: Output bias / hallucination affecting financial/contract review, unauthorized PII leakage, circuit breaker warning.
- **MEDIUM / LOW**: Minor drift, documentation gap, non-critical latency.

## 2. Automated Circuit Breakers
- **Thresholds**:
  - **1 CRITICAL** incident: Immediate emergency suspension.
  - **3 CRITICAL** or **5 HIGH** incidents within 24 hours: Automatic workspace deployment circuit breaker trip.
- **Action**: Deployment transitions to `SUSPENDED`.
- **Runtime Reaction**: All subsequent COSA runs and resumes fail fast with `DEPLOYMENT_NOT_APPROVED` / `DEPLOYMENT_SUSPENDED`. Zero calls reach model providers.

## 3. Incident Workflow
```
Detection -> Containment (Suspension) -> Investigation -> Notification Decision -> Remediation -> Integrity Verification -> Founder Reinstatement
```

### Step 1: Containment
If not automatically suspended, the Founder manually suspends the deployment via the Compliance Center panel or API:
```bash
POST /finance-legal/ai-deployments/:id/suspend
Body: {"reason": "Manual containment of suspected drift"}
```

### Step 2: Investigation & Evidence Preservation
- Fetch compliance snapshot and audit metadata.
- Audit records store canonical SHA-256 hashes and metadata, never raw prompts.
- Preserve tamper-evident evidence references.

### Step 3: Notification Decision
> [!IMPORTANT]
> COSA never sends an external legal or regulatory notification autonomously.
> The Founder reviews legal counsel advice, makes the notification decision, and records the formal decision and rationale in the incident record.

### Step 4: Remediation & Integrity Verification
- Apply data profile updates or model guardrail fixes.
- Run integrity verification on compliance snapshots:
```bash
POST /finance-legal/ai-compliance/snapshots/verify
```

### Step 5: Founder Reinstatement
Reinstatement requires Founder role, non-empty rationale, and verified snapshot:
```bash
POST /finance-legal/ai-deployments/:id/resume
Body: {"reason": "Remediation verified; guardrails updated and validated"}
```
Deployment transitions back to `APPROVED_FOR_USE`.
