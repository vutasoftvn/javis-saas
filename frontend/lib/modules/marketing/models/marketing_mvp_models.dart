import 'package:flutter/foundation.dart';

@immutable
class MarketingContextModel {
  final String id;
  final String workspaceId;
  final int revision;
  final String status;
  final Map<String, dynamic> productMarketing;
  final List<dynamic> icpSegments;
  final List<dynamic> customerResearchThemes;
  final List<dynamic> customerLanguage;
  final List<dynamic> evidence;
  final Map<String, dynamic>? offerArchitecture;
  final Map<String, dynamic>? twelveWeekPlan;

  const MarketingContextModel({
    required this.id,
    required this.workspaceId,
    this.revision = 1,
    this.status = 'draft',
    this.productMarketing = const {},
    this.icpSegments = const [],
    this.customerResearchThemes = const [],
    this.customerLanguage = const [],
    this.evidence = const [],
    this.offerArchitecture,
    this.twelveWeekPlan,
  });

  factory MarketingContextModel.fromJson(Map<String, dynamic> json) {
    return MarketingContextModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      revision: json['revision'] as int? ?? 1,
      status: json['status'] as String? ?? 'draft',
      productMarketing: json['productMarketing'] as Map<String, dynamic>? ?? json['product_marketing'] as Map<String, dynamic>? ?? {},
      icpSegments: json['icpSegments'] as List? ?? json['icp_segments'] as List? ?? [],
      customerResearchThemes: json['customerResearchThemes'] as List? ?? json['customer_research_themes'] as List? ?? [],
      customerLanguage: json['customerLanguage'] as List? ?? json['customer_language'] as List? ?? [],
      evidence: json['evidence'] as List? ?? [],
      offerArchitecture: json['offerArchitecture'] as Map<String, dynamic>? ?? json['offer_architecture'] as Map<String, dynamic>?,
      twelveWeekPlan: json['twelveWeekPlan'] as Map<String, dynamic>? ?? json['twelve_week_plan'] as Map<String, dynamic>?,
    );
  }
}

@immutable
class MarketingObjectiveModel {
  final String id;
  final String workspaceId;
  final String title;
  final String? description;
  final String status;
  final String? targetMetric;
  final double? targetValue;
  final double? currentValue;
  final DateTime? startDate;
  final DateTime? endDate;
  final DateTime createdAt;
  final DateTime updatedAt;

  const MarketingObjectiveModel({
    required this.id,
    required this.workspaceId,
    required this.title,
    this.description,
    required this.status,
    this.targetMetric,
    this.targetValue,
    this.currentValue,
    this.startDate,
    this.endDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MarketingObjectiveModel.fromJson(Map<String, dynamic> json) {
    return MarketingObjectiveModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      status: json['status'] as String? ?? 'active',
      targetMetric: json['targetMetric'] as String? ?? json['target_metric'] as String?,
      targetValue: (json['targetValue'] as num?)?.toDouble() ?? (json['target_value'] as num?)?.toDouble(),
      currentValue: (json['currentValue'] as num?)?.toDouble() ?? (json['current_value'] as num?)?.toDouble(),
      startDate: json['startDate'] != null ? DateTime.tryParse(json['startDate'] as String) : (json['start_date'] != null ? DateTime.tryParse(json['start_date'] as String) : null),
      endDate: json['endDate'] != null ? DateTime.tryParse(json['endDate'] as String) : (json['end_date'] != null ? DateTime.tryParse(json['end_date'] as String) : null),
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updatedAt'] as String? ?? json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class MarketingCampaignModel {
  final String id;
  final String workspaceId;
  final String name;
  final String funnelStage;
  final dynamic channels;
  final double? budget;
  final String status;
  final DateTime? startDate;
  final DateTime? endDate;
  final DateTime createdAt;
  final DateTime updatedAt;

  const MarketingCampaignModel({
    required this.id,
    required this.workspaceId,
    required this.name,
    required this.funnelStage,
    this.channels,
    this.budget,
    required this.status,
    this.startDate,
    this.endDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MarketingCampaignModel.fromJson(Map<String, dynamic> json) {
    return MarketingCampaignModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      funnelStage: json['funnelStage'] as String? ?? json['funnel_stage'] as String? ?? 'discover',
      channels: json['channels'],
      budget: (json['budget'] as num?)?.toDouble(),
      status: json['status'] as String? ?? 'draft',
      startDate: json['startDate'] != null ? DateTime.tryParse(json['startDate'] as String) : (json['start_date'] != null ? DateTime.tryParse(json['start_date'] as String) : null),
      endDate: json['endDate'] != null ? DateTime.tryParse(json['endDate'] as String) : (json['end_date'] != null ? DateTime.tryParse(json['end_date'] as String) : null),
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updatedAt'] as String? ?? json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class CampaignAssetModel {
  final String id;
  final String workspaceId;
  final String campaignId;
  final String assetType;
  final String title;
  final String content;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;

  const CampaignAssetModel({
    required this.id,
    required this.workspaceId,
    required this.campaignId,
    required this.assetType,
    required this.title,
    required this.content,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory CampaignAssetModel.fromJson(Map<String, dynamic> json) {
    return CampaignAssetModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      campaignId: json['campaignId'] as String? ?? json['campaign_id'] as String? ?? '',
      assetType: json['assetType'] as String? ?? json['asset_type'] as String? ?? '',
      title: json['title'] as String? ?? '',
      content: json['content'] as String? ?? '',
      status: json['status'] as String? ?? 'draft',
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updatedAt'] as String? ?? json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class MarketingExperimentModel {
  final String id;
  final String workspaceId;
  final String? campaignId;
  final String name;
  final String hypothesis;
  final String status;
  final String? baselineMetric;
  final double? baselineValue;
  final String? targetMetric;
  final double? targetValue;
  final double? actualValue;
  final String? conclusion;
  final DateTime createdAt;
  final DateTime updatedAt;

  const MarketingExperimentModel({
    required this.id,
    required this.workspaceId,
    this.campaignId,
    required this.name,
    required this.hypothesis,
    required this.status,
    this.baselineMetric,
    this.baselineValue,
    this.targetMetric,
    this.targetValue,
    this.actualValue,
    this.conclusion,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MarketingExperimentModel.fromJson(Map<String, dynamic> json) {
    return MarketingExperimentModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      campaignId: json['campaignId'] as String? ?? json['campaign_id'] as String?,
      name: json['name'] as String? ?? '',
      hypothesis: json['hypothesis'] as String? ?? '',
      status: json['status'] as String? ?? 'draft',
      baselineMetric: json['baselineMetric'] as String? ?? json['baseline_metric'] as String?,
      baselineValue: (json['baselineValue'] as num?)?.toDouble() ?? (json['baseline_value'] as num?)?.toDouble(),
      targetMetric: json['targetMetric'] as String? ?? json['target_metric'] as String?,
      targetValue: (json['targetValue'] as num?)?.toDouble() ?? (json['target_value'] as num?)?.toDouble(),
      actualValue: (json['actualValue'] as num?)?.toDouble() ?? (json['actual_value'] as num?)?.toDouble(),
      conclusion: json['conclusion'] as String?,
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updatedAt'] as String? ?? json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class MarketingObservedMetricModel {
  final String id;
  final String workspaceId;
  final String metricName;
  final String unit;
  final String providerKey;
  final String sourceRecordId;
  final DateTime observedAt;
  final DateTime ingestedAt;
  final double value;
  final dynamic metadata;

  const MarketingObservedMetricModel({
    required this.id,
    required this.workspaceId,
    required this.metricName,
    required this.unit,
    required this.providerKey,
    required this.sourceRecordId,
    required this.observedAt,
    required this.ingestedAt,
    required this.value,
    this.metadata,
  });

  factory MarketingObservedMetricModel.fromJson(Map<String, dynamic> json) {
    return MarketingObservedMetricModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      metricName: json['metricName'] as String? ?? json['metric_name'] as String? ?? '',
      unit: json['unit'] as String? ?? 'count',
      providerKey: json['providerKey'] as String? ?? json['provider_key'] as String? ?? '',
      sourceRecordId: json['sourceRecordId'] as String? ?? json['source_record_id'] as String? ?? '',
      observedAt: DateTime.tryParse(json['observedAt'] as String? ?? json['observed_at'] as String? ?? '') ?? DateTime.now(),
      ingestedAt: DateTime.tryParse(json['ingestedAt'] as String? ?? json['ingested_at'] as String? ?? '') ?? DateTime.now(),
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      metadata: json['metadata'],
    );
  }
}
