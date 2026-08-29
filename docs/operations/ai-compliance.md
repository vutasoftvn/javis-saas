# AI Compliance Operations Guide

## 1. Overview & Principles
JAVIS AI Compliance enforces statutory AI governance across the platform, strictly operating under the following non-negotiable principles:
- **Advisory-Only Baseline**: All AI capabilities operate exclusively in `ADVISORY_ONLY` mode. No autonomous decision-making in high-risk domains (HR, credit scoring, health, education, biometrics).
- **Statutory Floor Supremacy**: Statutory controls (`CURRENT_LAW`) supersede all workspace configurations. Tenant policies may restrict but can never relax statutory mandates.
- **Fail-Closed Architecture**: Any missing, unassessed, expired, or suspended compliance snapshot immediately denies model calls and external actions.
- **Data Minimization & Redaction**: PII (emails, phone numbers, citizen IDs) and confidential secrets are redacted before model ingestion.
- **Zero Raw Prompt/Output Storage**: System audit trails and event logs never store raw prompts, model outputs, or raw personal data.

## 2. Deployment Lifecycle
Deployments follow a strict state machine:
```
DRAFT -> ASSESSED -> APPROVED_FOR_USE <-> SUSPENDED -> RETIRED
```
1. **DRAFT**: System registered, baseline capabilities defined.
2. **ASSESSED**: Algorithmic impact assessment completed, statutory rules evaluated.
3. **APPROVED_FOR_USE**: Explicit Founder approval with rationale recorded; valid provider and data profiles verified.
4. **SUSPENDED**: Tripped by circuit breakers, critical incidents, or manual Founder emergency action.
5. **RETIRED**: Permanently decommissioned deployment.

## 3. Provider & Data Profiles
- Providers (e.g., DeepSeek, OpenAI) must possess an active `ProviderProfile` with non-training guarantees and encryption at rest/transit.
- Data categories (`PERSONAL`, `SENSITIVE_PERSONAL`, `BUSINESS_CONFIDENTIAL`) require active lawful basis and Founder authorization.
- Withdrawn authorizations immediately invalidate data use and block model calls.

## 4. Subject Rights & Retention Coordination
- Subject requests (Access, Correction, Erasure) are managed via `RetentionCoordinator`.
- **Legal Hold Precedence**: Active legal holds block erasure and record structured hold tombstones.
- When permissible, erasure purges object storage, episodic/semantic memory scopes, and knowledge index vectors.
