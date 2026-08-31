# Optional Workspace Orientation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Convert mandatory Vision/Mission/Core Values setup into an optional, editable Workspace Orientation feature that never blocks Hub access or invents organizational claims.

**Architecture:** Retain the three existing nullable columns and the existing compatibility endpoint, but make its update contract a partial patch that preserves omitted values and permits explicit clears. Replace the onboarding gate and modal with a voluntary Settings card; Hub authentication remains independent of orientation data. The UI performs no automatic AI drafting.

**Tech Stack:** TypeScript, Encore, Drizzle, Vitest, Flutter, GetX, flutter_test.

**Spec:** docs/superpowers/specs/2026-08-31-workspace-orientation-optional-design.md

## Global Constraints

- A workspace with vision, mission, and coreValues all null is valid and must not produce a setup prompt, readiness status, or access denial.
- Do not change or re-run the existing workspace-identity migration. The nullable columns and any saved content are retained.
- Keep the existing PATCH path and camelCase JSON keys for deployed-client compatibility: /identity/workspaces/:id/company-identity, vision, mission, coreValues.
- Omitted patch keys preserve stored values. Explicit null or whitespace-only text clears only that key.
- Do not derive availability, permission, UI copy, or completion from lifecycle stages W0_IDEA through W5_SCALE.
- Preserve the current verified workspace-membership authorization behavior; do not add roles or a founder-only policy in this change.
- No AgentChatService, SSE stream, generated Vision/Mission/Values, non-dismissible dialog, or automatic navigation may remain in the orientation feature.
- Start each behavior change with the specified focused failing test. Do not weaken existing test assertions to obtain a green result.
- Preserve user-owned changes; inspect git status --short before each task and stage only named files.

---

## File map

| Path | Responsibility after this plan |
| --- | --- |
| services/company/identity/services/workspace.service.ts | Partial, authenticated persistence of nullable orientation fields. |
| services/company/identity/handlers/workspace.handler.ts | Compatibility endpoint accepting optional nullable orientation keys. |
| services/company/identity/tests/workspace.test.ts | Regression coverage for partial update, explicit clear, empty patch, and workspace isolation. |
| frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart | Authentication only; no orientation fetch, modal, or callback seam. |
| frontend/lib/modules/settings/models/workspace_orientation.dart | Typed nullable orientation state with hasContent, never isComplete. |
| frontend/lib/modules/settings/services/workspace_orientation_service.dart | GET and compatibility PATCH client for the Settings card. |
| frontend/lib/modules/settings/views/widgets/workspace_orientation_settings_card.dart | Voluntary, editable Settings UI with truthful empty/error states. |
| frontend/lib/modules/settings/views/settings_view.dart | Adds the Workspace Orientation card to Settings. |
| frontend/lib/modules/onboarding/services/company_identity_gate.dart | Deleted blocking gate. |
| frontend/lib/modules/onboarding/widgets/company_identity_modal.dart | Deleted blocking modal and automatic AI-draft flow. |
| frontend/lib/modules/onboarding/services/company_identity_draft_parser.dart | Deleted parser used only by the removed AI-draft flow. |
| docs/superpowers/specs/2026-08-31-workspace-vision-mission-values-design.md | Historical, explicitly superseded decision record. |
| docs/superpowers/plans/2026-08-31-workspace-vision-mission-values.md | Historical, explicitly superseded implementation plan. |

## Task 1: Make the backend orientation patch partial and clearable

**Files:**

- Modify: services/company/identity/services/workspace.service.ts:143-188
- Modify: services/company/identity/handlers/workspace.handler.ts:40-67
- Modify: services/company/identity/tests/workspace.test.ts:30-105

**Interfaces:**

- Consumes: UpdateWorkspaceOrientationParams with workspaceId, authorization, and optional nullable vision, mission, coreValues keys.
- Produces: PATCH /identity/workspaces/:id/company-identity that returns Workspace with nullable vision, mission, coreValues.
- Invariant: an omitted key is preserved; a supplied null, empty string, or whitespace-only string becomes null.

- [ ] **Step 1: Replace required-all-fields tests with partial-patch regressions**

In services/company/identity/tests/workspace.test.ts, use the existing authorized-session fixture and add these tests:

    it("updates one supplied orientation field without overwriting the others", async () => {
      const session = await createTestSession({ displayName: "Orientation partial update" });
      await updateWorkspaceOrientationRecord({
        workspaceId: session.workspaceId,
        authorization: "Bearer " + session.accessToken,
        vision: "Original vision",
        mission: "Original mission",
        coreValues: "Original values",
      });

      const updated = await updateWorkspaceOrientationRecord({
        workspaceId: session.workspaceId,
        authorization: "Bearer " + session.accessToken,
        mission: "Updated mission",
      });

      expect(updated.vision).toBe("Original vision");
      expect(updated.mission).toBe("Updated mission");
      expect(updated.coreValues).toBe("Original values");
    });

    it("clears an explicitly supplied blank field", async () => {
      const session = await createTestSession({ displayName: "Orientation clear" });
      await updateWorkspaceOrientationRecord({
        workspaceId: session.workspaceId,
        authorization: "Bearer " + session.accessToken,
        vision: "A direction",
      });

      const updated = await updateWorkspaceOrientationRecord({
        workspaceId: session.workspaceId,
        authorization: "Bearer " + session.accessToken,
        vision: "   ",
      });

      expect(updated.vision).toBeNull();
    });

    it("rejects a patch with no orientation keys", async () => {
      const session = await createTestSession({ displayName: "Orientation empty patch" });

      await expect(
        updateWorkspaceOrientationRecord({
          workspaceId: session.workspaceId,
          authorization: "Bearer " + session.accessToken,
        })
      ).rejects.toThrow(/at least one orientation field/i);
    });

Retain and rename the current cross-workspace test so it calls updateWorkspaceOrientationRecord with one supplied field. Update the handler test so it sends only mission and asserts that nullable response fields are returned.

- [ ] **Step 2: Run the focused backend test and observe the old rejection**

Run:

    cd services/company && pnpm vitest run identity/tests/workspace.test.ts

Expected before implementation: TypeScript rejects the optional request shape or the service rejects because all three strings are not non-empty.

- [ ] **Step 3: Define the partial-patch service contract**

In services/company/identity/services/workspace.service.ts, replace the required-string fields with:

    export interface UpdateWorkspaceOrientationParams {
      workspaceId: string | number;
      authorization?: string;
      vision?: string | null;
      mission?: string | null;
      coreValues?: string | null;
    }

Rename updateWorkspaceCompanyIdentityRecord to updateWorkspaceOrientationRecord. Update all in-repository callers in this task; do not retain an alias after rg finds no old callers.

Add a normalizer and only update supplied keys:

    function normalizeOrientationText(value: string | null | undefined): string | null {
      return value?.trim() || null;
    }

    const patchFields = ["vision", "mission", "coreValues"] as const;
    const updates: {
      vision?: string | null;
      mission?: string | null;
      coreValues?: string | null;
    } = {};

    for (const field of patchFields) {
      if (Object.prototype.hasOwnProperty.call(params, field)) {
        updates[field] = normalizeOrientationText(params[field]);
      }
    }

    if (Object.keys(updates).length === 0) {
      throw APIError.invalidArgument("at least one orientation field must be provided");
    }

After resolveTenantContext verifies the caller, use .set({ ...updates, updatedAt: new Date() }). Do not check lifecycleStage and do not replace omitted values with null.

- [ ] **Step 4: Make the existing endpoint accept optional nullable keys**

In services/company/identity/handlers/workspace.handler.ts, preserve the PATCH path but route it to updateWorkspaceOrientationRecord. Its input type is:

    {
      id: string;
      authorization?: Header<"Authorization">;
      vision?: string | null;
      mission?: string | null;
      coreValues?: string | null;
    }

Pass each property through unchanged. GET continues returning the existing nullable Workspace fields. Do not add a new endpoint or change response-key casing.

- [ ] **Step 5: Verify backend behavior and static contracts**

Run:

    cd services/company && pnpm typecheck && pnpm vitest run identity/tests/workspace.test.ts

Expected: partial update preserves other fields, blank clears the specified field, no-key patch returns invalidArgument, and cross-workspace write is still rejected.

- [ ] **Step 6: Commit the independently deployable backend compatibility change**

    git add services/company/identity/services/workspace.service.ts services/company/identity/handlers/workspace.handler.ts services/company/identity/tests/workspace.test.ts
    git commit -m "refactor(identity): make workspace orientation optional"

## Task 2: Remove orientation from Hub authentication and delete the blocking gate

**Files:**

- Modify: frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart:1-60
- Modify: frontend/test/hologram_hub_test.dart:92-132
- Delete: frontend/lib/modules/onboarding/services/company_identity_gate.dart
- Delete: frontend/test/company_identity_gate_test.dart

**Interfaces:**

- Produces: Future<void> HubAuthMixin.ensureAuthenticated() with no companyIdentityCheck argument.
- Invariant: a successful auth response is sufficient to enter Hub even when the current workspace has no orientation data.

- [ ] **Step 1: Write the non-blocking authentication regression**

Replace the Company Identity Gate test group in frontend/test/hologram_hub_test.dart with:

    test("ensureAuthenticated does not fetch or prompt for workspace orientation", () async {
      final requestedPaths = <String>[];
      ApiClient.client = MockClient((request) async {
        requestedPaths.add(request.url.path);
        if (request.url.path == "/identity/me") {
          return http.Response('{"display_name":"Test User","role":"member"}', 200);
        }
        return http.Response("not found", 404);
      });

      AuthService.setCachedToken("test_token");
      final controller = HologramHubController();
      await controller.ensureAuthenticated();

      expect(requestedPaths, ["/identity/me"]);
    });

Keep the existing authenticated-user assertions if they are in the same test group.

- [ ] **Step 2: Run the focused Flutter test and observe the old behavior**

Run:

    cd frontend && flutter test test/hologram_hub_test.dart

Expected before implementation: the test records GET /identity/workspaces/<workspace_id> after the auth request.

- [ ] **Step 3: Make Hub authentication independent of orientation**

In hub_auth_mixin.dart:

1. Remove imports for SecureStorageService and CompanyIdentityGate.
2. Remove the optional companyIdentityCheck parameter from ensureAuthenticated.
3. Remove the workspace_id read and the entire CompanyIdentityGate.checkAndPrompt call.
4. Leave token validation, profile display-name update, role display update, and login redirect behavior untouched.

The final method calls authService.getMe exactly once for this flow and never calls an orientation service.

- [ ] **Step 4: Delete the gate and gate-specific tests**

Delete company_identity_gate.dart and company_identity_gate_test.dart. The in-flight loop, Get.dialog call, re-fetch loop, non-dismissible dialog requirement, and modal production-path test are all behavior being removed, not behavior to retain under another name.

- [ ] **Step 5: Verify no automatic gate survives**

Run:

    cd frontend && flutter test test/hologram_hub_test.dart
    rg -n "CompanyIdentityGate|companyIdentityCheck|checkAndPrompt" lib test

Expected: the focused test passes and rg returns no matches.

- [ ] **Step 6: Commit the non-blocking access correction**

    git add frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart frontend/test/hologram_hub_test.dart
    git rm frontend/lib/modules/onboarding/services/company_identity_gate.dart frontend/test/company_identity_gate_test.dart
    git commit -m "fix(hub): remove mandatory workspace orientation gate"

## Task 3: Replace the onboarding modal with a voluntary Settings card

**Files:**

- Create: frontend/lib/modules/settings/models/workspace_orientation.dart
- Create: frontend/lib/modules/settings/services/workspace_orientation_service.dart
- Create: frontend/lib/modules/settings/views/widgets/workspace_orientation_settings_card.dart
- Modify: frontend/lib/modules/settings/views/settings_view.dart:1-42
- Delete: frontend/lib/data/models/workspace_company_identity_model.dart
- Delete: frontend/lib/modules/onboarding/services/company_identity_service.dart
- Delete: frontend/lib/modules/onboarding/widgets/company_identity_modal.dart
- Delete: frontend/lib/modules/onboarding/services/company_identity_draft_parser.dart
- Create: frontend/test/workspace_orientation_service_test.dart
- Create: frontend/test/workspace_orientation_settings_card_test.dart
- Delete: frontend/test/workspace_company_identity_model_test.dart
- Delete: frontend/test/company_identity_service_test.dart
- Delete: frontend/test/company_identity_modal_test.dart
- Delete: frontend/test/company_identity_draft_parser_test.dart

**Interfaces:**

- WorkspaceOrientation has workspaceId, nullable vision/mission/coreValues, and bool get hasContent.
- WorkspaceOrientationService.fetch(String workspaceId) returns Future<WorkspaceOrientation>.
- WorkspaceOrientationService.update(String workspaceId, {required String? vision, required String? mission, required String? coreValues}) sends the editor snapshot keys, including explicit JSON null keys.
- WorkspaceOrientationSettingsCard renders without a workspace ID as an unavailable state; it never redirects or opens a dialog.

- [ ] **Step 1: Write focused Settings client and UI tests**

Create frontend/test/workspace_orientation_service_test.dart. Verify:

1. GET parses all-null fields and result.hasContent is false.
2. PATCH uses the existing path and sends explicit null values without treating them as an error.
3. A non-200 response throws WorkspaceOrientationException.

Use this exact partial-clear request assertion:

    expect(request.method, "PATCH");
    expect(request.url.path, "/identity/workspaces/ws_1/company-identity");
    expect(request.body, '{"vision":null,"mission":"Focus on customer discovery","coreValues":null}');

Create frontend/test/workspace_orientation_settings_card_test.dart with an injected fake service and workspace-ID reader. Cover:

1. A null workspace ID renders Chưa chọn workspace and no form fields.
2. A fetched all-null orientation renders Chưa xác định and a voluntary Thêm định hướng action, not a dialog.
3. Saving only Mission sends vision null, Mission text, and coreValues null.
4. Xóa định hướng calls update with three null fields and returns to the truthful empty state.
5. A fetch or save error renders a visible error message and keeps the user in Settings.

- [ ] **Step 2: Run the new tests and observe missing types/widgets**

Run:

    cd frontend && flutter test test/workspace_orientation_service_test.dart test/workspace_orientation_settings_card_test.dart

Expected before implementation: imports and WorkspaceOrientation types do not exist.

- [ ] **Step 3: Implement the Settings-scoped model and client**

Create workspace_orientation.dart:

    class WorkspaceOrientation {
      const WorkspaceOrientation({
        required this.workspaceId,
        this.vision,
        this.mission,
        this.coreValues,
      });

      final String workspaceId;
      final String? vision;
      final String? mission;
      final String? coreValues;

      bool get hasContent =>
          (vision?.trim().isNotEmpty ?? false) ||
          (mission?.trim().isNotEmpty ?? false) ||
          (coreValues?.trim().isNotEmpty ?? false);
    }

Implement nullable JSON parsing only. Do not expose isComplete.

Implement WorkspaceOrientationService.update with:

    final res = await ApiClient.patch(
      '/identity/workspaces/$workspaceId/company-identity',
      body: {
        'vision': vision?.trim().isEmpty ?? true ? null : vision?.trim(),
        'mission': mission?.trim().isEmpty ?? true ? null : mission?.trim(),
        'coreValues': coreValues?.trim().isEmpty ?? true ? null : coreValues?.trim(),
      },
    );

Return parsed WorkspaceOrientation for HTTP 200 and throw WorkspaceOrientationException for every other status. Do not import AgentChatService.

- [ ] **Step 4: Implement the voluntary Settings card**

Create WorkspaceOrientationSettingsCard as a StatefulWidget with optional dependency injection:

    const WorkspaceOrientationSettingsCard({
      super.key,
      this.service,
      this.readWorkspaceId,
    });

    final WorkspaceOrientationService? service;
    final Future<String?> Function()? readWorkspaceId;

The production default calls SecureStorageService.read("workspace_id"). On load, fetch only when workspace ID is non-empty. Render these states:

- Chưa chọn workspace: no workspace context is available.
- Chưa xác định: all three values are null or blank; this is valid.
- Định hướng workspace: editable Vision, Mission, and Nguyên tắc không muốn đánh đổi fields.
- Lỗi tải hoặc lưu: visible error copy plus Thử lại.

Use an in-page Card. Do not call Get.dialog, Navigator.pop, PopScope, or barrierDismissible. Put Thêm định hướng into the empty state, Lưu thay đổi into edit state, and Xóa định hướng only when hasContent. Delete writes three null values and refreshes the card from returned server state.

- [ ] **Step 5: Mount the card in Settings and delete the old implementation**

In settings_view.dart import WorkspaceOrientationSettingsCard and place it above AiGatewaySettingsCard:

    children: const [
      WorkspaceOrientationSettingsCard(),
      SizedBox(height: 12),
      AiGatewaySettingsCard(),
    ],

Delete the old model, onboarding client, modal, parser, and their focused tests. They encode invalid semantics: isComplete, non-dismissible gating, and ungrounded AI/SSE generation.

Run:

    rg -n "CompanyIdentityModal|CompanyIdentityService|CompanyIdentityDraft|parseCompanyIdentityDraft" frontend/lib frontend/test

Expected: no matches. Inspect unrelated AgentChatService matches before retaining them.

- [ ] **Step 6: Verify the Settings feature**

Run:

    cd frontend && flutter test test/workspace_orientation_service_test.dart test/workspace_orientation_settings_card_test.dart
    flutter analyze

Expected: focused tests and static analysis pass; Settings supports empty, partial, saved, cleared, and error states without automatic prompt.

- [ ] **Step 7: Commit the optional UI replacement**

    git add frontend/lib/modules/settings/models/workspace_orientation.dart frontend/lib/modules/settings/services/workspace_orientation_service.dart frontend/lib/modules/settings/views/widgets/workspace_orientation_settings_card.dart frontend/lib/modules/settings/views/settings_view.dart frontend/test/workspace_orientation_service_test.dart frontend/test/workspace_orientation_settings_card_test.dart
    git rm frontend/lib/data/models/workspace_company_identity_model.dart frontend/lib/modules/onboarding/services/company_identity_service.dart frontend/lib/modules/onboarding/widgets/company_identity_modal.dart frontend/lib/modules/onboarding/services/company_identity_draft_parser.dart frontend/test/workspace_company_identity_model_test.dart frontend/test/company_identity_service_test.dart frontend/test/company_identity_modal_test.dart frontend/test/company_identity_draft_parser_test.dart
    git commit -m "refactor(settings): make workspace orientation voluntary"

## Task 4: Preserve documentation truth and prove the complete adjustment

**Files:**

- Modify: docs/superpowers/specs/2026-08-31-workspace-vision-mission-values-design.md:1-9
- Modify: docs/superpowers/plans/2026-08-31-workspace-vision-mission-values.md:1-3
- Create: docs/superpowers/specs/2026-08-31-workspace-orientation-optional-design.md
- Create: docs/superpowers/plans/2026-08-31-workspace-orientation-optional.md

- [ ] **Step 1: Confirm the historical documents are visibly superseded**

The old design must have a Superseded status and link to the new design. The old plan must start with a Superseded notice pointing to this plan. Do not delete them; they explain why the code previously contained a hard gate.

Run:

    rg -n "chặn cứng Hub|barrierDismissible: false|Founder phải thiết lập" docs/superpowers/specs docs/superpowers/plans

Expected: remaining matches occur only below the superseded notices in historical documents, never in an active plan/spec.

- [ ] **Step 2: Run proportional verification**

Run:

    cd services/company && pnpm typecheck && pnpm vitest run identity/tests/workspace.test.ts
    cd ../../frontend && flutter test test/hologram_hub_test.dart test/workspace_orientation_service_test.dart test/workspace_orientation_settings_card_test.dart
    flutter analyze
    flutter test
    cd .. && make contract-freeze-check

Expected: server partial-patch and Flutter non-blocking/optional UI tests pass; full Flutter suite, analyzer, and contract freeze remain green.

- [ ] **Step 3: Inspect for lifecycle and gate regressions**

Run:

    rg -n "lifecycleStage.*[Vv]ision|[Vv]ision.*lifecycleStage|W0_IDEA.*[Vv]ision|CompanyIdentityGate|CompanyIdentityModal" services/company frontend/lib frontend/test
    git diff --check
    git status --short

Expected: no code path binds orientation to lifecycle stage or automatic access gating. Legacy phrase matches occur only in superseded documents.

- [ ] **Step 4: Commit the documentation cutoff**

    git add docs/superpowers/specs/2026-08-31-workspace-vision-mission-values-design.md docs/superpowers/plans/2026-08-31-workspace-vision-mission-values.md docs/superpowers/specs/2026-08-31-workspace-orientation-optional-design.md docs/superpowers/plans/2026-08-31-workspace-orientation-optional.md
    git commit -m "docs(product): make workspace orientation optional"

## Final verification checklist

- [ ] Empty orientation never blocks authentication, navigation, or Hub rendering.
- [ ] Existing values remain stored; partial updates preserve omitted values; explicit blanks clear only supplied values.
- [ ] The compatibility PATCH endpoint and camelCase response keys are unchanged.
- [ ] No migration, lifecycle condition, company-readiness inference, or new role is introduced.
- [ ] The voluntary Settings card is the only entry point and has truthful empty and error states.
- [ ] The automatic AI draft, SSE parser, modal, and gate have been deleted.
- [ ] Historical mandatory documents are labeled Superseded and all relevant backend/Flutter quality gates pass.
