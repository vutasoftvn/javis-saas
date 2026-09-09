// GENERATED FILE — DO NOT MODIFY DIRECTLY
// Source: shared/contracts/mvp-surface.json · Generator: scripts/gen-mvp-contracts.mjs
// To update: edit shared/contracts/mvp-surface.json and run `node scripts/gen-mvp-contracts.mjs`

import 'api_result.dart';

enum MvpEndpoint {
  commercialContactCreate(
    id: 'commercial.contact.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/contacts',
    requiresWorkspace: true,
  ),
  commercialInterviewCreate(
    id: 'commercial.interview.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/interviews',
    requiresWorkspace: true,
  ),
  commercialInterviewSubmitEvidence(
    id: 'commercial.interview.submit_evidence',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/interviews/:id/submit-evidence',
    requiresWorkspace: true,
  ),
  commercialLeadCreate(
    id: 'commercial.lead.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/leads',
    requiresWorkspace: true,
  ),
  financeBudgetSummaryRead(
    id: 'finance.budget_summary.read',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/finance/budget-summary',
    requiresWorkspace: true,
  ),
  financeSnapshotLatest(
    id: 'finance.snapshot.latest',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/finance/snapshots/latest',
    requiresWorkspace: true,
  ),
  marketingCampaignCreate(
    id: 'marketing.campaign.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/marketing/campaigns',
    requiresWorkspace: true,
  ),
  marketingCampaignList(
    id: 'marketing.campaign.list',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/campaigns',
    requiresWorkspace: true,
  ),
  marketingExperimentCreate(
    id: 'marketing.experiment.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/commercial/marketing/experiments',
    requiresWorkspace: true,
  ),
  marketingExperimentList(
    id: 'marketing.experiment.list',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/experiments',
    requiresWorkspace: true,
  ),
  settingsCapabilityManifestRead(
    id: 'settings.capability_manifest.read',
    enabled: true,
    plane: ApiPlane.platform,
    method: 'GET',
    path: '/platform/workspaces/:workspaceId/capability-manifest',
    requiresWorkspace: true,
  ),
  strategyAssumptionCreate(
    id: 'strategy.assumption.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/assumptions',
    requiresWorkspace: true,
  ),
  strategyAssumptionsRanked(
    id: 'strategy.assumptions.ranked',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/strategy/projects/:projectId/ranked-assumptions',
    requiresWorkspace: true,
  ),
  strategyDecisionCreate(
    id: 'strategy.decision.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/decision-records',
    requiresWorkspace: true,
  ),
  strategyEvidenceReview(
    id: 'strategy.evidence.review',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/evidence/:id/review',
    requiresWorkspace: true,
  ),
  strategyFounderBriefRead(
    id: 'strategy.founder_brief.read',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/projects/:projectId/founder-brief',
    requiresWorkspace: true,
  ),
  strategyFounderTrialBoardRead(
    id: 'strategy.founder_trial.board.read',
    enabled: true,
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/projects/:projectId/founder-trial-board',
    requiresWorkspace: true,
  ),
  strategyFounderTrialExperimentCreate(
    id: 'strategy.founder_trial.experiment.create',
    enabled: true,
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/projects/:projectId/founder-trial/experiments',
    requiresWorkspace: true,
  ),
  strategyOperatingCycleResize(
    id: 'strategy.operating_cycle.resize',
    enabled: true,
    plane: ApiPlane.company,
    method: 'PATCH',
    path: '/operations/projects/:projectId/operating-cycle',
    requiresWorkspace: true,
  );

  const MvpEndpoint({
    required this.id,
    required this.enabled,
    required this.plane,
    required this.method,
    required this.path,
    required this.requiresWorkspace,
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
