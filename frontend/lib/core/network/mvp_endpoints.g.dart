// GENERATED FILE — DO NOT MODIFY DIRECTLY
// Source: shared/contracts/mvp-surface.json · Generator: scripts/gen-mvp-contracts.mjs
// To update: edit shared/contracts/mvp-surface.json and run `node scripts/gen-mvp-contracts.mjs`

import 'api_result.dart';

enum MvpEndpoint {
  agentKnowledgeProjectSearch(
    id: 'agent.knowledge.project.search',
    enabled: true,
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/knowledge/projects/:projectId/search',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  commercialContactCreate(
    id: 'commercial.contact.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/contacts',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  commercialInterviewCreate(
    id: 'commercial.interview.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/interviews',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  commercialInterviewSubmitEvidence(
    id: 'commercial.interview.submit_evidence',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/interviews/:id/submit-evidence',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  commercialLeadCreate(
    id: 'commercial.lead.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/leads',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  financeBudgetSummaryRead(
    id: 'finance.budget_summary.read',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/finance/budget-summary',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  financeSnapshotLatest(
    id: 'finance.snapshot.latest',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/finance/snapshots/latest',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  identityAgentCapabilityGrantCreate(
    id: 'identity.agent_capability_grant.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/identity/agent-capability-grants',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  identityAgentCapabilityGrantRevoke(
    id: 'identity.agent_capability_grant.revoke',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/identity/agent-capability-grants/:grantId/revoke',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  identityPermissionsRead(
    id: 'identity.permissions.read',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/identity/permissions',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  identityPermissionsSimulate(
    id: 'identity.permissions.simulate',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/identity/permissions/simulate',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  identityPermissionsWrite(
    id: 'identity.permissions.write',
    enabled: true,
    plane: ApiPlane.company,
    method: 'PUT',
    path: '/identity/permissions',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  marketingCampaignCreate(
    id: 'marketing.campaign.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/marketing/campaigns',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  marketingCampaignList(
    id: 'marketing.campaign.list',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/campaigns',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  marketingExperimentCreate(
    id: 'marketing.experiment.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/marketing/experiments',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  marketingExperimentList(
    id: 'marketing.experiment.list',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/experiments',
    requiresWorkspace: true,
    requiresProject: false,
  ),
  projectCommitmentWrite(
    id: 'project.commitment.write',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/projects/:projectId/operating-loop/commitments',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  projectCycleWrite(
    id: 'project.cycle.write',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/projects/:projectId/operating-loop/cycles',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  projectLoopRead(
    id: 'project.loop.read',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/projects/:projectId/operating-loop',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  projectOkrWrite(
    id: 'project.okr.write',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/projects/:projectId/operating-loop/objectives',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  projectTaskWrite(
    id: 'project.task.write',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/projects/:projectId/operating-loop/tasks',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  projectWeekWrite(
    id: 'project.week.write',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/projects/:projectId/operating-loop/weeks',
    requiresWorkspace: true,
    requiresProject: true,
  ),
  settingsCapabilityManifestRead(
    id: 'settings.capability_manifest.read',
    enabled: true,
    plane: ApiPlane.platform,
    method: 'GET',
    path: '/platform/workspaces/:workspaceId/capability-manifest',
    requiresWorkspace: true,
    requiresProject: false,
  );

  const MvpEndpoint({
    required this.id,
    required this.enabled,
    required this.plane,
    required this.method,
    required this.path,
    required this.requiresWorkspace,
    required this.requiresProject,
  });

  final String id;
  // Fix-review (2026-09-02, final review I-4) — `shared/contracts/mvp-surface.json`
  // đánh dấu `enabled: false` cho các capability chưa có backend thật (vd. vault.*);
  // trước đây field này không được emit ra Dart nên client Flutter không có cách
  // nào tự chặn gọi một endpoint đã biết trước là chưa khả dụng.
  final bool enabled;
  final ApiPlane plane;
  final String method;
  final String path;
  final bool requiresWorkspace;
  final bool requiresProject;

  static MvpEndpoint? fromId(String id) {
    for (final endpoint in MvpEndpoint.values) {
      if (endpoint.id == id) return endpoint;
    }
    return null;
  }

  static MvpEndpoint byId(String id) {
    final endpoint = fromId(id);
    if (endpoint == null) {
      throw ArgumentError.value(id, 'id', 'Unknown MvpEndpoint ID');
    }
    return endpoint;
  }
}
