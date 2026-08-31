// GENERATED FILE — DO NOT MODIFY DIRECTLY
// Source: shared/contracts/mvp-surface.json · Generator: scripts/gen-mvp-contracts.mjs
// To update: edit shared/contracts/mvp-surface.json and run `node scripts/gen-mvp-contracts.mjs`

import 'api_result.dart';

enum MvpEndpoint {
  marketingAssetList(
    id: 'marketing.asset.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/assets',
    requiresWorkspace: true,
  ),
  marketingCampaignList(
    id: 'marketing.campaign.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/campaigns',
    requiresWorkspace: true,
  ),
  marketingContextGet(
    id: 'marketing.context.get',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing-context',
    requiresWorkspace: true,
  ),
  marketingContextUpdate(
    id: 'marketing.context.update',
    plane: ApiPlane.company,
    method: 'PUT',
    path: '/commercial/marketing-context',
    requiresWorkspace: true,
  ),
  marketingExperimentList(
    id: 'marketing.experiment.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/experiments',
    requiresWorkspace: true,
  ),
  marketingMetricObserved(
    id: 'marketing.metric.observed',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/metrics/observed',
    requiresWorkspace: true,
  ),
  marketingObjectiveList(
    id: 'marketing.objective.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/commercial/marketing/objectives',
    requiresWorkspace: true,
  ),
  settingsAuditEventList(
    id: 'settings.audit_event.list',
    plane: ApiPlane.platform,
    method: 'GET',
    path: '/platform/workspaces/:workspaceId/audit-events',
    requiresWorkspace: true,
  ),
  settingsConnectorInstall(
    id: 'settings.connector.install',
    plane: ApiPlane.platform,
    method: 'POST',
    path: '/platform/workspaces/:workspaceId/connectors/:connectorKey/install',
    requiresWorkspace: true,
  ),
  settingsConnectorList(
    id: 'settings.connector.list',
    plane: ApiPlane.platform,
    method: 'GET',
    path: '/platform/workspaces/:workspaceId/connectors',
    requiresWorkspace: true,
  ),
  settingsConnectorRevoke(
    id: 'settings.connector.revoke',
    plane: ApiPlane.platform,
    method: 'POST',
    path: '/platform/workspaces/:workspaceId/connectors/:connectorKey/revoke',
    requiresWorkspace: true,
  ),
  settingsMemberList(
    id: 'settings.member.list',
    plane: ApiPlane.platform,
    method: 'GET',
    path: '/platform/workspaces/:workspaceId/members',
    requiresWorkspace: true,
  ),
  settingsRuntimeNodeList(
    id: 'settings.runtime_node.list',
    plane: ApiPlane.platform,
    method: 'GET',
    path: '/platform/workspaces/:workspaceId/runtime-nodes',
    requiresWorkspace: true,
  ),
  settingsRuntimeNodeRevoke(
    id: 'settings.runtime_node.revoke',
    plane: ApiPlane.platform,
    method: 'POST',
    path: '/platform/workspaces/:workspaceId/runtime-nodes/:nodeId/revoke',
    requiresWorkspace: true,
  ),
  settingsSkillList(
    id: 'settings.skill.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/settings/skills',
    requiresWorkspace: true,
  ),
  settingsSkillUpdate(
    id: 'settings.skill.update',
    plane: ApiPlane.agent,
    method: 'PUT',
    path: '/agent/settings/skills/:skillKey',
    requiresWorkspace: true,
  ),
  strategyCanvasCreate(
    id: 'strategy.canvas.create',
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/canvases',
    requiresWorkspace: true,
  ),
  strategyCanvasDelete(
    id: 'strategy.canvas.delete',
    plane: ApiPlane.company,
    method: 'DELETE',
    path: '/operations/strategy/canvases/:id',
    requiresWorkspace: true,
  ),
  strategyCanvasGet(
    id: 'strategy.canvas.get',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/strategy/canvases/:id',
    requiresWorkspace: true,
  ),
  strategyCanvasList(
    id: 'strategy.canvas.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/strategy/canvases',
    requiresWorkspace: true,
  ),
  strategyCanvasRevisionApprove(
    id: 'strategy.canvas.revision.approve',
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/canvas-revisions/:id/approve',
    requiresWorkspace: true,
  ),
  strategyCanvasRevisionCreate(
    id: 'strategy.canvas.revision.create',
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/canvases/:id/revisions',
    requiresWorkspace: true,
  ),
  strategyCanvasRevisionGet(
    id: 'strategy.canvas.revision.get',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/strategy/canvas-revisions/:id',
    requiresWorkspace: true,
  ),
  strategyCanvasRevisionReject(
    id: 'strategy.canvas.revision.reject',
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/canvas-revisions/:id/reject',
    requiresWorkspace: true,
  ),
  strategyCanvasRevisionSubmitReview(
    id: 'strategy.canvas.revision.submit_review',
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/strategy/canvas-revisions/:id/submit-review',
    requiresWorkspace: true,
  ),
  strategyCanvasUpdate(
    id: 'strategy.canvas.update',
    plane: ApiPlane.company,
    method: 'PUT',
    path: '/operations/strategy/canvases/:id',
    requiresWorkspace: true,
  ),
  strategyFundingMatches(
    id: 'strategy.funding.matches',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/strategy/funding-matches',
    requiresWorkspace: true,
  ),
  strategyObjectiveDelete(
    id: 'strategy.objective.delete',
    plane: ApiPlane.company,
    method: 'DELETE',
    path: '/operations/objectives/:id',
    requiresWorkspace: true,
  ),
  strategyObjectiveList(
    id: 'strategy.objective.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/objectives',
    requiresWorkspace: true,
  ),
  strategyObjectiveProgress(
    id: 'strategy.objective.progress',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/objectives/:id/progress',
    requiresWorkspace: true,
  ),
  strategyOkrCycleList(
    id: 'strategy.okr_cycle.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/okr-cycles',
    requiresWorkspace: true,
  ),
  strategyTwelveWeekCommitmentList(
    id: 'strategy.twelve_week.commitment.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/twelve-week-commitments',
    requiresWorkspace: true,
  ),
  strategyTwelveWeekCycleList(
    id: 'strategy.twelve_week.cycle.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/twelve-week-cycles',
    requiresWorkspace: true,
  ),
  strategyTwelveWeekPlanList(
    id: 'strategy.twelve_week.plan.list',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/twelve-week-plans',
    requiresWorkspace: true,
  ),
  vaultDocumentConfirmUpload(
    id: 'vault.document.confirm_upload',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/vault/documents/:id/confirm',
    requiresWorkspace: true,
  ),
  vaultDocumentDelete(
    id: 'vault.document.delete',
    plane: ApiPlane.agent,
    method: 'DELETE',
    path: '/agent/vault/documents/:id',
    requiresWorkspace: true,
  ),
  vaultDocumentGet(
    id: 'vault.document.get',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/vault/documents/:id',
    requiresWorkspace: true,
  ),
  vaultDocumentList(
    id: 'vault.document.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/vault/documents',
    requiresWorkspace: true,
  ),
  vaultDocumentUploadTicket(
    id: 'vault.document.upload_ticket',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/vault/documents/upload-ticket',
    requiresWorkspace: true,
  ),
  vaultKnowledgeGraph(
    id: 'vault.knowledge.graph',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/vault/knowledge/graph',
    requiresWorkspace: true,
  ),
  vaultKnowledgeIndexedSources(
    id: 'vault.knowledge.indexed_sources',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/vault/knowledge/sources',
    requiresWorkspace: true,
  ),
  vaultKnowledgeRetrievalQuery(
    id: 'vault.knowledge.retrieval_query',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/vault/retrieval/query',
    requiresWorkspace: true,
  ),
  workforceApprovalDecision(
    id: 'workforce.approval.decision',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/workforce/approvals/:approvalId/decision',
    requiresWorkspace: true,
  ),
  workforceApprovalList(
    id: 'workforce.approval.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/approvals',
    requiresWorkspace: true,
  ),
  workforceAssignmentCreate(
    id: 'workforce.assignment.create',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/workforce/assignments',
    requiresWorkspace: true,
  ),
  workforceAssignmentList(
    id: 'workforce.assignment.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/assignments',
    requiresWorkspace: true,
  ),
  workforceAssignmentRetire(
    id: 'workforce.assignment.retire',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/workforce/assignments/:id/retire',
    requiresWorkspace: true,
  ),
  workforceCapabilityList(
    id: 'workforce.capability.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/capabilities',
    requiresWorkspace: true,
  ),
  workforceCompositionGet(
    id: 'workforce.composition.get',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/composition',
    requiresWorkspace: true,
  ),
  workforceCostObservationList(
    id: 'workforce.cost_observation.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/cost-observations',
    requiresWorkspace: true,
  ),
  workforceHealthGet(
    id: 'workforce.health.get',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/health',
    requiresWorkspace: true,
  ),
  workforceOrgChartGet(
    id: 'workforce.org_chart.get',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/org-chart',
    requiresWorkspace: true,
  ),
  workforceRunArtifacts(
    id: 'workforce.run.artifacts',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/runs/:runId/artifacts',
    requiresWorkspace: true,
  ),
  workforceRunEvents(
    id: 'workforce.run.events',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/runs/:runId/events',
    requiresWorkspace: true,
  ),
  workforceRunGet(
    id: 'workforce.run.get',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/runs/:runId',
    requiresWorkspace: true,
  ),
  workforceRunList(
    id: 'workforce.run.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/runs',
    requiresWorkspace: true,
  ),
  workforceScheduleCreate(
    id: 'workforce.schedule.create',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/workforce/schedules',
    requiresWorkspace: true,
  ),
  workforceScheduleList(
    id: 'workforce.schedule.list',
    plane: ApiPlane.agent,
    method: 'GET',
    path: '/agent/workforce/schedules',
    requiresWorkspace: true,
  ),
  workforceScheduleRunNow(
    id: 'workforce.schedule.run_now',
    plane: ApiPlane.agent,
    method: 'POST',
    path: '/agent/workforce/schedules/:scheduleId/run-now',
    requiresWorkspace: true,
  ),
  workspaceRuntimeBlockers(
    id: 'workspace_runtime.blockers',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/workspace-runtime/blockers',
    requiresWorkspace: true,
  ),
  workspaceRuntimeItemGet(
    id: 'workspace_runtime.item_get',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/workspace-runtime/items/:sourceKind/:sourceId',
    requiresWorkspace: true,
  ),
  workspaceRuntimeItemSnooze(
    id: 'workspace_runtime.item_snooze',
    plane: ApiPlane.company,
    method: 'POST',
    path: '/operations/workspace-runtime/items/:sourceKind/:sourceId/snooze',
    requiresWorkspace: true,
  ),
  workspaceRuntimeNeedsYou(
    id: 'workspace_runtime.needs_you',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/workspace-runtime/needs-you',
    requiresWorkspace: true,
  ),
  workspaceRuntimeSourceStatus(
    id: 'workspace_runtime.source_status',
    plane: ApiPlane.company,
    method: 'GET',
    path: '/operations/workspace-runtime/source-status',
    requiresWorkspace: true,
  );

  const MvpEndpoint({
    required this.id,
    required this.plane,
    required this.method,
    required this.path,
    required this.requiresWorkspace,
  });

  final String id;
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
