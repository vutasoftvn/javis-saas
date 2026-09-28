class AiInitiativePortfolioItem {
  final String initiativeId;
  final int initiativeRevision;
  final String title;
  final String? description;
  final String lifecycleState;
  final String riskTier;
  final String autonomyTier;
  final String businessOwnerMemberId;
  final String? technicalOwnerMemberId;
  final String? riskOwnerMemberId;
  final String? baselineMetricValue;
  final String? targetMetricValue;
  final String? latestOutcomeValue;
  final String? metricUnit;
  final String costBudgetStatus;
  final String adoptionStatus;
  final String qualityStatus;
  final String dataReadinessStatus;
  final String nextRequiredGate;
  final List<String> blockingReasons;
  final List<String> authorizedActions;
  final String? latestDecisionId;

  const AiInitiativePortfolioItem({
    required this.initiativeId,
    required this.initiativeRevision,
    required this.title,
    this.description,
    required this.lifecycleState,
    required this.riskTier,
    required this.autonomyTier,
    required this.businessOwnerMemberId,
    this.technicalOwnerMemberId,
    this.riskOwnerMemberId,
    this.baselineMetricValue,
    this.targetMetricValue,
    this.latestOutcomeValue,
    this.metricUnit,
    required this.costBudgetStatus,
    required this.adoptionStatus,
    required this.qualityStatus,
    required this.dataReadinessStatus,
    required this.nextRequiredGate,
    this.blockingReasons = const [],
    this.authorizedActions = const [],
    this.latestDecisionId,
  });

  factory AiInitiativePortfolioItem.fromJson(Map<String, dynamic> json) {
    return AiInitiativePortfolioItem(
      initiativeId: json['initiativeId'] as String? ?? json['initiative_id'] as String? ?? '',
      initiativeRevision: json['initiativeRevision'] as int? ?? json['initiative_revision'] as int? ?? 1,
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      lifecycleState: json['lifecycleState'] as String? ?? json['lifecycle_state'] as String? ?? 'DISCOVER',
      riskTier: json['riskTier'] as String? ?? json['risk_tier'] as String? ?? 'LOW',
      autonomyTier: json['autonomyTier'] as String? ?? json['autonomy_tier'] as String? ?? 'A0',
      businessOwnerMemberId: json['businessOwnerMemberId'] as String? ?? json['business_owner_member_id'] as String? ?? '',
      technicalOwnerMemberId: json['technicalOwnerMemberId'] as String? ?? json['technical_owner_member_id'] as String?,
      riskOwnerMemberId: json['riskOwnerMemberId'] as String? ?? json['risk_owner_member_id'] as String?,
      baselineMetricValue: json['baselineMetricValue'] as String? ?? json['baseline_metric_value'] as String?,
      targetMetricValue: json['targetMetricValue'] as String? ?? json['target_metric_value'] as String?,
      latestOutcomeValue: json['latestOutcomeValue'] as String? ?? json['latest_outcome_value'] as String?,
      metricUnit: json['metricUnit'] as String? ?? json['metric_unit'] as String?,
      costBudgetStatus: json['costBudgetStatus'] as String? ?? json['cost_budget_status'] as String? ?? 'NOT_CONFIGURED',
      adoptionStatus: json['adoptionStatus'] as String? ?? json['adoption_status'] as String? ?? 'NO_DATA',
      qualityStatus: json['qualityStatus'] as String? ?? json['quality_status'] as String? ?? 'NO_EVAL',
      dataReadinessStatus: json['dataReadinessStatus'] as String? ?? json['data_readiness_status'] as String? ?? 'NO_ASSESSMENT',
      nextRequiredGate: json['nextRequiredGate'] as String? ?? json['next_required_gate'] as String? ?? '',
      blockingReasons: (json['blockingReasons'] as List<dynamic>? ?? json['blocking_reasons'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      authorizedActions: (json['authorizedActions'] as List<dynamic>? ?? json['authorized_actions'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      latestDecisionId: json['latestDecisionId'] as String? ?? json['latest_decision_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'initiativeId': initiativeId,
      'initiativeRevision': initiativeRevision,
      'title': title,
      'description': description,
      'lifecycleState': lifecycleState,
      'riskTier': riskTier,
      'autonomyTier': autonomyTier,
      'businessOwnerMemberId': businessOwnerMemberId,
      'technicalOwnerMemberId': technicalOwnerMemberId,
      'riskOwnerMemberId': riskOwnerMemberId,
      'baselineMetricValue': baselineMetricValue,
      'targetMetricValue': targetMetricValue,
      'latestOutcomeValue': latestOutcomeValue,
      'metricUnit': metricUnit,
      'costBudgetStatus': costBudgetStatus,
      'adoptionStatus': adoptionStatus,
      'qualityStatus': qualityStatus,
      'dataReadinessStatus': dataReadinessStatus,
      'nextRequiredGate': nextRequiredGate,
      'blockingReasons': blockingReasons,
      'authorizedActions': authorizedActions,
      'latestDecisionId': latestDecisionId,
    };
  }
}

class AiInitiativePortfolioResponse {
  final String projectId;
  final String workspaceId;
  final List<AiInitiativePortfolioItem> items;
  final int totalCount;

  const AiInitiativePortfolioResponse({
    required this.projectId,
    required this.workspaceId,
    required this.items,
    required this.totalCount,
  });

  factory AiInitiativePortfolioResponse.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? [];
    final parsedItems = rawItems
        .whereType<Map<String, dynamic>>()
        .map((e) => AiInitiativePortfolioItem.fromJson(e))
        .toList();

    return AiInitiativePortfolioResponse(
      projectId: json['projectId'] as String? ?? json['project_id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      items: parsedItems,
      totalCount: json['totalCount'] as int? ?? json['total_count'] as int? ?? parsedItems.length,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'projectId': projectId,
      'workspaceId': workspaceId,
      'items': items.map((e) => e.toJson()).toList(),
      'totalCount': totalCount,
    };
  }
}
