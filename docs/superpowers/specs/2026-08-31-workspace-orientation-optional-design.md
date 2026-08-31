# Optional Workspace Orientation Design

**Status:** Approved for implementation planning

**Date:** 2026-08-31

**Supersedes:** docs/superpowers/specs/2026-08-31-workspace-vision-mission-values-design.md

## Decision

Vision, Mission, and Core Values are optional workspace orientation notes. They are not an onboarding requirement, a lifecycle-stage requirement, an authorization condition, a readiness signal, or a prerequisite for opening the Command Center.

The product must serve individuals, students, early teams, startups, and companies without implying that a formal company statement exists or is required. A workspace with no orientation content is a valid, truthful state.

## Why this adjustment is needed

The current implementation blocks Hub access whenever one of three free-text fields is absent. That forces early-stage users to manufacture formal statements before they have a team, customer evidence, or a stable organization. It also gives AI a prompt that can produce generic claims mistaken for real company direction.

The fields still have value later: a team may voluntarily use them to document alignment, decision principles, recruitment context, or external communication. That value does not justify making them universal or immutable.

## Product behavior

### User-facing language

The settings feature is named **Định hướng workspace**. It uses these optional prompts:

- Đích đến dài hạn (Vision)
- Vấn đề/kết quả đang hướng tới (Mission)
- Nguyên tắc không muốn đánh đổi (Core Values)

The card explains that it is optional and useful only when the user or team wants a shared reference. It must not infer that the workspace is a legal company, ready to scale, or incomplete because the fields are empty.

### Availability

- No modal is opened at login, workspace creation, route change, or Hub initialization.
- The feature is available from Cài đặt hệ thống as a voluntary workspace settings card.
- No lifecycle stage W0 through W5 changes availability, validation, copy, or permissions.
- The current workspace member authorization remains unchanged; this adjustment does not introduce new roles or a founder-only restriction.

### Editing and empty state

Each field is independently optional:

- A user may save one, two, all three, or none.
- An explicit blank value clears that field.
- An omitted API field leaves its current value unchanged.
- All fields absent or null is represented as Chưa xác định; it is not an error or a prompt trigger.
- Existing saved content is retained and becomes editable. There is no one-time lock.

### AI truthfulness

The automatic “Nhờ AI soạn” flow is removed from this feature. The orientation card does not ask AI to invent Vision, Mission, or Values from an empty workspace. A future AI assistant may help edit user-provided evidence or notes only under a separately approved, source-grounded design.

## Technical design

The existing nullable columns in core.workspaces remain unchanged:

    vision TEXT NULL
    mission TEXT NULL
    core_values TEXT NULL

No migration is required, and existing content is preserved.

The existing endpoint path remains for compatibility:

    PATCH /identity/workspaces/:id/company-identity

Its request semantics change to a partial patch:

    {
      "vision"?: string | null,
      "mission"?: string | null,
      "coreValues"?: string | null
    }

At least one key must be present. When a key is present, whitespace-only string normalizes to null and clears that stored field. When a key is absent, the stored field is preserved. GET continues returning nullable camelCase values.

The backend keeps the existing verified workspace-membership check. It must not use lifecycle stage to determine whether writing is allowed.

Frontend renames the internal concept from CompanyIdentity to WorkspaceOrientation. The new model exposes hasContent, not isComplete. The old blocking gate, non-dismissible modal, draft parser, and direct AgentChatService use are deleted.

## Data flow

    SettingsView
      -> WorkspaceOrientationSettingsCard
      -> WorkspaceOrientationService.fetch / update
      -> Company Identity compatibility endpoint
      -> verified workspace membership
      -> core.workspaces nullable orientation columns

Hub authentication performs only ordinary authentication. It does not call the orientation service and does not fetch workspace identity as a side effect.

## Acceptance criteria

1. A new or existing workspace with all three fields null can authenticate and use Hub normally.
2. Any member who was previously allowed to update the fields can save one orientation field, update one field without overwriting another, and explicitly clear saved content.
3. A request with no patch keys is rejected as invalid input; a cross-workspace caller remains rejected.
4. Settings shows a truthful empty state and never opens automatically.
5. The orientation UI contains no AgentChatService, SSE, generated statement, non-dismissible modal, or lifecycle-stage condition.
6. Existing persisted statements remain readable and editable after deployment.
7. Backend and Flutter focused tests, type checks, and relevant quality gates pass.

## Out of scope

- Changing workspace roles or adding an approval workflow for orientation edits.
- Creating a legal-company profile, organization classification, score, maturity label, or stage promotion rule.
- Restoring or reusing the 12-week planning vision_statement or weekly-plan mission fields; those remain planning artifacts with separate meaning.
- Building a source-grounded AI writing assistant.
