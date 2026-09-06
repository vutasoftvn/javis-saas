import 'package:flutter/foundation.dart';

// ---------------------------------------------------------------------------
// ENUMS WITH TOLERANT READ (unknown) AND STRICT WRITE
// ---------------------------------------------------------------------------

enum StrategyMethod {
  classic,
  bscFilter,
  unknown;

  static StrategyMethod fromString(String? val) {
    if (val == null) return StrategyMethod.unknown;
    switch (val.toUpperCase()) {
      case 'CLASSIC':
        return StrategyMethod.classic;
      case 'BSC_FILTER':
        return StrategyMethod.bscFilter;
      default:
        return StrategyMethod.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case StrategyMethod.classic:
        return 'CLASSIC';
      case StrategyMethod.bscFilter:
        return 'BSC_FILTER';
      case StrategyMethod.unknown:
        throw StateError('Cannot serialize unknown StrategyMethod');
    }
  }
}

enum BscMode {
  off,
  optional,
  required,
  unknown;

  static BscMode fromString(String? val) {
    if (val == null) return BscMode.unknown;
    switch (val.toUpperCase()) {
      case 'OFF':
        return BscMode.off;
      case 'OPTIONAL':
        return BscMode.optional;
      case 'REQUIRED':
        return BscMode.required;
      default:
        return BscMode.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case BscMode.off:
        return 'OFF';
      case BscMode.optional:
        return 'OPTIONAL';
      case BscMode.required:
        return 'REQUIRED';
      case BscMode.unknown:
        throw StateError('Cannot serialize unknown BscMode');
    }
  }
}

enum BscPerspective {
  financial,
  customer,
  internalProcess,
  learningAndGrowth,
  unknown;

  static BscPerspective fromString(String? val) {
    if (val == null) return BscPerspective.unknown;
    switch (val.toUpperCase()) {
      case 'FINANCIAL':
        return BscPerspective.financial;
      case 'CUSTOMER':
        return BscPerspective.customer;
      case 'INTERNAL_PROCESS':
        return BscPerspective.internalProcess;
      case 'LEARNING_AND_GROWTH':
        return BscPerspective.learningAndGrowth;
      default:
        return BscPerspective.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case BscPerspective.financial:
        return 'FINANCIAL';
      case BscPerspective.customer:
        return 'CUSTOMER';
      case BscPerspective.internalProcess:
        return 'INTERNAL_PROCESS';
      case BscPerspective.learningAndGrowth:
        return 'LEARNING_AND_GROWTH';
      case BscPerspective.unknown:
        throw StateError('Cannot serialize unknown BscPerspective');
    }
  }

  String get displayNameVi {
    switch (this) {
      case BscPerspective.financial:
        return 'Tài chính';
      case BscPerspective.customer:
        return 'Khách hàng';
      case BscPerspective.internalProcess:
        return 'Quy trình nội bộ';
      case BscPerspective.learningAndGrowth:
        return 'Học hỏi & Phát triển';
      case BscPerspective.unknown:
        return 'Khác';
    }
  }
}

enum MidCycleReviewPolicy {
  off,
  auto,
  custom,
  unknown;

  static MidCycleReviewPolicy fromString(String? val) {
    if (val == null) return MidCycleReviewPolicy.unknown;
    switch (val.toUpperCase()) {
      case 'OFF':
        return MidCycleReviewPolicy.off;
      case 'AUTO':
        return MidCycleReviewPolicy.auto;
      case 'CUSTOM':
        return MidCycleReviewPolicy.custom;
      default:
        return MidCycleReviewPolicy.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case MidCycleReviewPolicy.off:
        return 'OFF';
      case MidCycleReviewPolicy.auto:
        return 'AUTO';
      case MidCycleReviewPolicy.custom:
        return 'CUSTOM';
      case MidCycleReviewPolicy.unknown:
        throw StateError('Cannot serialize unknown MidCycleReviewPolicy');
    }
  }
}

enum ApprovalPolicy {
  founderOnly,
  delegatedApprover,
  unknown;

  static ApprovalPolicy fromString(String? val) {
    if (val == null) return ApprovalPolicy.unknown;
    switch (val.toUpperCase()) {
      case 'FOUNDER_ONLY':
        return ApprovalPolicy.founderOnly;
      case 'DELEGATED_APPROVER':
        return ApprovalPolicy.delegatedApprover;
      default:
        return ApprovalPolicy.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case ApprovalPolicy.founderOnly:
        return 'FOUNDER_ONLY';
      case ApprovalPolicy.delegatedApprover:
        return 'DELEGATED_APPROVER';
      case ApprovalPolicy.unknown:
        throw StateError('Cannot serialize unknown ApprovalPolicy');
    }
  }
}

enum PestelDimension {
  political,
  economic,
  social,
  technological,
  environmental,
  legal,
  unknown;

  static PestelDimension fromString(String? val) {
    if (val == null) return PestelDimension.unknown;
    switch (val.toUpperCase()) {
      case 'POLITICAL':
        return PestelDimension.political;
      case 'ECONOMIC':
        return PestelDimension.economic;
      case 'SOCIAL':
        return PestelDimension.social;
      case 'TECHNOLOGICAL':
        return PestelDimension.technological;
      case 'ENVIRONMENTAL':
        return PestelDimension.environmental;
      case 'LEGAL':
        return PestelDimension.legal;
      default:
        return PestelDimension.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case PestelDimension.political:
        return 'POLITICAL';
      case PestelDimension.economic:
        return 'ECONOMIC';
      case PestelDimension.social:
        return 'SOCIAL';
      case PestelDimension.technological:
        return 'TECHNOLOGICAL';
      case PestelDimension.environmental:
        return 'ENVIRONMENTAL';
      case PestelDimension.legal:
        return 'LEGAL';
      case PestelDimension.unknown:
        throw StateError('Cannot serialize unknown PestelDimension');
    }
  }

  String get displayNameVi {
    switch (this) {
      case PestelDimension.political:
        return 'Chính trị (Political)';
      case PestelDimension.economic:
        return 'Kinh tế (Economic)';
      case PestelDimension.social:
        return 'Xã hội (Social)';
      case PestelDimension.technological:
        return 'Công nghệ (Technological)';
      case PestelDimension.environmental:
        return 'Môi trường (Environmental)';
      case PestelDimension.legal:
        return 'Pháp lý (Legal)';
      case PestelDimension.unknown:
        return 'Khác';
    }
  }
}

enum ResourceCapabilityCategory {
  financialResource,
  humanOrganizationalCapability,
  intellectualDataIpAsset,
  technologyOperationalAsset,
  marketRelationshipAsset,
  governanceLegalRiskCapability,
  unknown;

  static ResourceCapabilityCategory fromString(String? val) {
    if (val == null) return ResourceCapabilityCategory.unknown;
    switch (val.toUpperCase()) {
      case 'FINANCIAL_RESOURCE':
        return ResourceCapabilityCategory.financialResource;
      case 'HUMAN_ORGANIZATIONAL_CAPABILITY':
        return ResourceCapabilityCategory.humanOrganizationalCapability;
      case 'INTELLECTUAL_DATA_IP_ASSET':
        return ResourceCapabilityCategory.intellectualDataIpAsset;
      case 'TECHNOLOGY_OPERATIONAL_ASSET':
        return ResourceCapabilityCategory.technologyOperationalAsset;
      case 'MARKET_RELATIONSHIP_ASSET':
        return ResourceCapabilityCategory.marketRelationshipAsset;
      case 'GOVERNANCE_LEGAL_RISK_CAPABILITY':
        return ResourceCapabilityCategory.governanceLegalRiskCapability;
      default:
        return ResourceCapabilityCategory.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case ResourceCapabilityCategory.financialResource:
        return 'FINANCIAL_RESOURCE';
      case ResourceCapabilityCategory.humanOrganizationalCapability:
        return 'HUMAN_ORGANIZATIONAL_CAPABILITY';
      case ResourceCapabilityCategory.intellectualDataIpAsset:
        return 'INTELLECTUAL_DATA_IP_ASSET';
      case ResourceCapabilityCategory.technologyOperationalAsset:
        return 'TECHNOLOGY_OPERATIONAL_ASSET';
      case ResourceCapabilityCategory.marketRelationshipAsset:
        return 'MARKET_RELATIONSHIP_ASSET';
      case ResourceCapabilityCategory.governanceLegalRiskCapability:
        return 'GOVERNANCE_LEGAL_RISK_CAPABILITY';
      case ResourceCapabilityCategory.unknown:
        throw StateError('Cannot serialize unknown ResourceCapabilityCategory');
    }
  }

  String get displayNameVi {
    switch (this) {
      case ResourceCapabilityCategory.financialResource:
        return 'Nguồn lực tài chính';
      case ResourceCapabilityCategory.humanOrganizationalCapability:
        return 'Năng lực nhân sự & tổ chức';
      case ResourceCapabilityCategory.intellectualDataIpAsset:
        return 'Tài sản trí tuệ & dữ liệu';
      case ResourceCapabilityCategory.technologyOperationalAsset:
        return 'Tài sản công nghệ & vận hành';
      case ResourceCapabilityCategory.marketRelationshipAsset:
        return 'Mối quan hệ & thị trường';
      case ResourceCapabilityCategory.governanceLegalRiskCapability:
        return 'Năng lực pháp lý, quản trị & rủi ro';
      case ResourceCapabilityCategory.unknown:
        return 'Khác';
    }
  }
}

enum SwotItemType {
  strength,
  weakness,
  opportunity,
  threat,
  unknown;

  static SwotItemType fromString(String? val) {
    if (val == null) return SwotItemType.unknown;
    switch (val.toUpperCase()) {
      case 'STRENGTH':
        return SwotItemType.strength;
      case 'WEAKNESS':
        return SwotItemType.weakness;
      case 'OPPORTUNITY':
        return SwotItemType.opportunity;
      case 'THREAT':
        return SwotItemType.threat;
      default:
        return SwotItemType.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case SwotItemType.strength:
        return 'STRENGTH';
      case SwotItemType.weakness:
        return 'WEAKNESS';
      case SwotItemType.opportunity:
        return 'OPPORTUNITY';
      case SwotItemType.threat:
        return 'THREAT';
      case SwotItemType.unknown:
        throw StateError('Cannot serialize unknown SwotItemType');
    }
  }

  String get displayNameVi {
    switch (this) {
      case SwotItemType.strength:
        return 'Điểm mạnh (Strengths)';
      case SwotItemType.weakness:
        return 'Điểm yếu (Weaknesses)';
      case SwotItemType.opportunity:
        return 'Cơ hội (Opportunities)';
      case SwotItemType.threat:
        return 'Thách thức (Threats)';
      case SwotItemType.unknown:
        return 'Khác';
    }
  }
}

enum TowsOptionType {
  so,
  wo,
  st,
  wt,
  unknown;

  static TowsOptionType fromString(String? val) {
    if (val == null) return TowsOptionType.unknown;
    switch (val.toUpperCase()) {
      case 'SO':
        return TowsOptionType.so;
      case 'WO':
        return TowsOptionType.wo;
      case 'ST':
        return TowsOptionType.st;
      case 'WT':
        return TowsOptionType.wt;
      default:
        return TowsOptionType.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case TowsOptionType.so:
        return 'SO';
      case TowsOptionType.wo:
        return 'WO';
      case TowsOptionType.st:
        return 'ST';
      case TowsOptionType.wt:
        return 'WT';
      case TowsOptionType.unknown:
        throw StateError('Cannot serialize unknown TowsOptionType');
    }
  }

  String get displayNameVi {
    switch (this) {
      case TowsOptionType.so:
        return 'SO (Điểm mạnh - Cơ hội)';
      case TowsOptionType.wo:
        return 'WO (Điểm yếu - Cơ hội)';
      case TowsOptionType.st:
        return 'ST (Điểm mạnh - Thách thức)';
      case TowsOptionType.wt:
        return 'WT (Điểm yếu - Thách thức)';
      case TowsOptionType.unknown:
        return 'Khác';
    }
  }
}

enum TowsOptionStatus {
  draft,
  selected,
  rejected,
  unknown;

  static TowsOptionStatus fromString(String? val) {
    if (val == null) return TowsOptionStatus.unknown;
    switch (val.toUpperCase()) {
      case 'DRAFT':
        return TowsOptionStatus.draft;
      case 'SELECTED':
        return TowsOptionStatus.selected;
      case 'REJECTED':
        return TowsOptionStatus.rejected;
      default:
        return TowsOptionStatus.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case TowsOptionStatus.draft:
        return 'DRAFT';
      case TowsOptionStatus.selected:
        return 'SELECTED';
      case TowsOptionStatus.rejected:
        return 'REJECTED';
      case TowsOptionStatus.unknown:
        throw StateError('Cannot serialize unknown TowsOptionStatus');
    }
  }
}

enum CycleReviewKind {
  weekly,
  midCycle,
  endCycle,
  unknown;

  static CycleReviewKind fromString(String? val) {
    if (val == null) return CycleReviewKind.unknown;
    switch (val.toUpperCase()) {
      case 'WEEKLY':
        return CycleReviewKind.weekly;
      case 'MID_CYCLE':
        return CycleReviewKind.midCycle;
      case 'END_CYCLE':
        return CycleReviewKind.endCycle;
      default:
        return CycleReviewKind.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case CycleReviewKind.weekly:
        return 'WEEKLY';
      case CycleReviewKind.midCycle:
        return 'MID_CYCLE';
      case CycleReviewKind.endCycle:
        return 'END_CYCLE';
      case CycleReviewKind.unknown:
        throw StateError('Cannot serialize unknown CycleReviewKind');
    }
  }

  String get displayNameVi {
    switch (this) {
      case CycleReviewKind.weekly:
        return 'Đánh giá hàng tuần (Weekly)';
      case CycleReviewKind.midCycle:
        return 'Đánh giá giữa chu kỳ (Mid-cycle)';
      case CycleReviewKind.endCycle:
        return 'Tổng kết chu kỳ (End-cycle)';
      case CycleReviewKind.unknown:
        return 'Khác';
    }
  }
}

enum CycleReviewStatus {
  scheduled,
  inProgress,
  completed,
  skipped,
  superseded,
  unknown;

  static CycleReviewStatus fromString(String? val) {
    if (val == null) return CycleReviewStatus.unknown;
    switch (val.toUpperCase()) {
      case 'SCHEDULED':
        return CycleReviewStatus.scheduled;
      case 'IN_PROGRESS':
        return CycleReviewStatus.inProgress;
      case 'COMPLETED':
        return CycleReviewStatus.completed;
      case 'SKIPPED':
        return CycleReviewStatus.skipped;
      case 'SUPERSEDED':
        return CycleReviewStatus.superseded;
      default:
        return CycleReviewStatus.unknown;
    }
  }

  String toApiString() {
    switch (this) {
      case CycleReviewStatus.scheduled:
        return 'SCHEDULED';
      case CycleReviewStatus.inProgress:
        return 'IN_PROGRESS';
      case CycleReviewStatus.completed:
        return 'COMPLETED';
      case CycleReviewStatus.skipped:
        return 'SKIPPED';
      case CycleReviewStatus.superseded:
        return 'SUPERSEDED';
      case CycleReviewStatus.unknown:
        throw StateError('Cannot serialize unknown CycleReviewStatus');
    }
  }
}

// ---------------------------------------------------------------------------
// IMMUTABLE DTO MODELS
// ---------------------------------------------------------------------------

@immutable
class WorkspaceStrategySettingsModel {
  final String workspaceId;
  final StrategyMethod strategyMethod;
  final BscMode bscMode;
  final List<BscPerspective> enabledBscPerspectives;
  final int towsSelectionLimit;
  final bool weeklyReviewEnabled;
  final MidCycleReviewPolicy midCycleReviewPolicy;
  final bool endCycleReviewEnabled;
  final List<String> allowedAgentProfiles;
  final ApprovalPolicy approvalPolicy;
  final int revision;
  final bool canEdit;
  final String? updatedByMemberId;
  final String? updatedAt;

  int get maxTowsSelections => towsSelectionLimit;

  const WorkspaceStrategySettingsModel({
    required this.workspaceId,
    required this.strategyMethod,
    required this.bscMode,
    this.enabledBscPerspectives = const [],
    int? towsSelectionLimit,
    int? maxTowsSelections,
    this.weeklyReviewEnabled = true,
    this.midCycleReviewPolicy = MidCycleReviewPolicy.off,
    this.endCycleReviewEnabled = true,
    this.allowedAgentProfiles = const [],
    this.approvalPolicy = ApprovalPolicy.founderOnly,
    this.revision = 1,
    this.canEdit = true,
    this.updatedByMemberId,
    this.updatedAt,
  }) : towsSelectionLimit = towsSelectionLimit ?? maxTowsSelections ?? 1;

  factory WorkspaceStrategySettingsModel.fromJson(Map<String, dynamic> json) {
    final perspectivesRaw = (json['enabledBscPerspectives'] as List<dynamic>?) ?? [];
    final profilesRaw = (json['allowedAgentProfiles'] as List<dynamic>?) ?? [];

    return WorkspaceStrategySettingsModel(
      workspaceId: json['workspaceId']?.toString() ?? '',
      strategyMethod: StrategyMethod.fromString(json['strategyMethod']?.toString()),
      bscMode: BscMode.fromString(json['bscMode']?.toString()),
      enabledBscPerspectives: perspectivesRaw
          .map((p) => BscPerspective.fromString(p?.toString()))
          .where((p) => p != BscPerspective.unknown)
          .toList(),
      towsSelectionLimit: json['towsSelectionLimit'] is int ? json['towsSelectionLimit'] as int : 1,
      weeklyReviewEnabled: json['weeklyReviewEnabled'] == true,
      midCycleReviewPolicy: MidCycleReviewPolicy.fromString(json['midCycleReviewPolicy']?.toString()),
      endCycleReviewEnabled: json['endCycleReviewEnabled'] != false,
      allowedAgentProfiles: profilesRaw.map((p) => p.toString()).toList(),
      approvalPolicy: ApprovalPolicy.fromString(json['approvalPolicy']?.toString()),
      revision: json['revision'] is int ? json['revision'] as int : 1,
      canEdit: json['canEdit'] != false,
      updatedByMemberId: json['updatedByMemberId']?.toString(),
      updatedAt: json['updatedAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'workspaceId': workspaceId,
      'strategyMethod': strategyMethod.toApiString(),
      'bscMode': bscMode.toApiString(),
      'enabledBscPerspectives': enabledBscPerspectives.map((p) => p.toApiString()).toList(),
      'towsSelectionLimit': towsSelectionLimit,
      'weeklyReviewEnabled': weeklyReviewEnabled,
      'midCycleReviewPolicy': midCycleReviewPolicy.toApiString(),
      'endCycleReviewEnabled': endCycleReviewEnabled,
      'allowedAgentProfiles': allowedAgentProfiles,
      'approvalPolicy': approvalPolicy.toApiString(),
      'revision': revision,
    };
  }
}

@immutable
class BscFocusScopeModel {
  final String id;
  final String strategicObjectiveId;
  final BscPerspective perspective;
  final String focusDescription;
  final double weight;

  const BscFocusScopeModel({
    required this.id,
    required this.strategicObjectiveId,
    required this.perspective,
    required this.focusDescription,
    required this.weight,
  });

  factory BscFocusScopeModel.fromJson(Map<String, dynamic> json) {
    return BscFocusScopeModel(
      id: json['id']?.toString() ?? '',
      strategicObjectiveId: json['strategicObjectiveId']?.toString() ?? '',
      perspective: BscPerspective.fromString(json['perspective']?.toString()),
      focusDescription: json['focusDescription']?.toString() ?? '',
      weight: (json['weight'] is num) ? (json['weight'] as num).toDouble() : 1.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'strategicObjectiveId': strategicObjectiveId,
      'perspective': perspective.toApiString(),
      'focusDescription': focusDescription,
      'weight': weight,
    };
  }
}

@immutable
class StrategicObjectiveModel {
  final String id;
  final String workspaceId;
  final String? projectId;
  final String title;
  final String? successDefinition;
  final String? timeHorizonEnd;
  final String status;
  final String? ownerMemberId;
  final int revision;
  final List<BscFocusScopeModel> bscFocusScopes;
  final String? createdAt;
  final String? updatedAt;

  const StrategicObjectiveModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    required this.title,
    this.successDefinition,
    this.timeHorizonEnd,
    required this.status,
    this.ownerMemberId,
    required this.revision,
    this.bscFocusScopes = const [],
    this.createdAt,
    this.updatedAt,
  });

  factory StrategicObjectiveModel.fromJson(Map<String, dynamic> json) {
    final scopesRaw = (json['bscFocusScopes'] as List<dynamic>?) ?? [];
    return StrategicObjectiveModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString(),
      title: json['title']?.toString() ?? '',
      successDefinition: json['successDefinition']?.toString(),
      timeHorizonEnd: json['timeHorizonEnd']?.toString(),
      status: json['status']?.toString() ?? 'DRAFT',
      ownerMemberId: json['ownerMemberId']?.toString(),
      revision: json['revision'] is int ? json['revision'] as int : 1,
      bscFocusScopes: scopesRaw
          .map((s) => BscFocusScopeModel.fromJson(s as Map<String, dynamic>))
          .toList(),
      createdAt: json['createdAt']?.toString(),
      updatedAt: json['updatedAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'projectId': projectId,
      'title': title,
      'successDefinition': successDefinition,
      'timeHorizonEnd': timeHorizonEnd,
      'status': status,
      'ownerMemberId': ownerMemberId,
      'revision': revision,
      'bscFocusScopes': bscFocusScopes.map((s) => s.toJson()).toList(),
    };
  }
}

@immutable
class PestelSignalModel {
  final String id;
  final String workspaceId;
  final String strategicObjectiveId;
  final PestelDimension dimension;
  final String statement;
  final String impact;
  final String certainty;
  final List<String> evidenceRefs;
  final List<BscPerspective> bscPerspectives;
  final String status;
  final int revision;
  final String? createdAt;

  const PestelSignalModel({
    required this.id,
    required this.workspaceId,
    required this.strategicObjectiveId,
    required this.dimension,
    required this.statement,
    required this.impact,
    required this.certainty,
    this.evidenceRefs = const [],
    this.bscPerspectives = const [],
    required this.status,
    required this.revision,
    this.createdAt,
  });

  factory PestelSignalModel.fromJson(Map<String, dynamic> json) {
    final refsRaw = (json['evidenceRefs'] as List<dynamic>?) ?? [];
    final bscRaw = (json['bscPerspectives'] as List<dynamic>?) ?? [];

    return PestelSignalModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      strategicObjectiveId: json['strategicObjectiveId']?.toString() ?? '',
      dimension: PestelDimension.fromString(json['dimension']?.toString()),
      statement: json['statement']?.toString() ?? '',
      impact: json['impact']?.toString() ?? 'MEDIUM',
      certainty: json['certainty']?.toString() ?? 'MEDIUM',
      evidenceRefs: refsRaw.map((e) => e.toString()).toList(),
      bscPerspectives: bscRaw
          .map((p) => BscPerspective.fromString(p?.toString()))
          .where((p) => p != BscPerspective.unknown)
          .toList(),
      status: json['status']?.toString() ?? 'DRAFT',
      revision: json['revision'] is int ? json['revision'] as int : 1,
      createdAt: json['createdAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'strategicObjectiveId': strategicObjectiveId,
      'dimension': dimension.toApiString(),
      'statement': statement,
      'impact': impact,
      'certainty': certainty,
      'evidenceRefs': evidenceRefs,
      'bscPerspectives': bscPerspectives.map((p) => p.toApiString()).toList(),
      'status': status,
      'revision': revision,
    };
  }
}

@immutable
class ResourceCapabilityAssessmentModel {
  final String id;
  final String workspaceId;
  final String strategicObjectiveId;
  final ResourceCapabilityCategory category;
  final String statement;
  final String maturityLevel;
  final bool isStrength;
  final List<String> evidenceRefs;
  final List<BscPerspective> bscPerspectives;
  final int revision;

  const ResourceCapabilityAssessmentModel({
    required this.id,
    required this.workspaceId,
    required this.strategicObjectiveId,
    required this.category,
    required this.statement,
    required this.maturityLevel,
    required this.isStrength,
    this.evidenceRefs = const [],
    this.bscPerspectives = const [],
    required this.revision,
  });

  factory ResourceCapabilityAssessmentModel.fromJson(Map<String, dynamic> json) {
    final refsRaw = (json['evidenceRefs'] as List<dynamic>?) ?? [];
    final bscRaw = (json['bscPerspectives'] as List<dynamic>?) ?? [];

    return ResourceCapabilityAssessmentModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      strategicObjectiveId: json['strategicObjectiveId']?.toString() ?? '',
      category: ResourceCapabilityCategory.fromString(json['category']?.toString()),
      statement: json['statement']?.toString() ?? '',
      maturityLevel: json['maturityLevel']?.toString() ?? 'BASIC',
      isStrength: json['isStrength'] == true,
      evidenceRefs: refsRaw.map((e) => e.toString()).toList(),
      bscPerspectives: bscRaw
          .map((p) => BscPerspective.fromString(p?.toString()))
          .where((p) => p != BscPerspective.unknown)
          .toList(),
      revision: json['revision'] is int ? json['revision'] as int : 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'strategicObjectiveId': strategicObjectiveId,
      'category': category.toApiString(),
      'statement': statement,
      'maturityLevel': maturityLevel,
      'isStrength': isStrength,
      'evidenceRefs': evidenceRefs,
      'bscPerspectives': bscPerspectives.map((p) => p.toApiString()).toList(),
      'revision': revision,
    };
  }
}

@immutable
class SwotItemModel {
  final String id;
  final String workspaceId;
  final String strategicObjectiveId;
  final SwotItemType itemType;
  final String content;
  final String? sourcePestelSignalId;
  final String? sourceResourceCapabilityId;
  final List<String> evidenceRefs;
  final List<BscPerspective> bscPerspectives;
  final int revision;

  const SwotItemModel({
    required this.id,
    required this.workspaceId,
    required this.strategicObjectiveId,
    required this.itemType,
    required this.content,
    this.sourcePestelSignalId,
    this.sourceResourceCapabilityId,
    this.evidenceRefs = const [],
    this.bscPerspectives = const [],
    required this.revision,
  });

  factory SwotItemModel.fromJson(Map<String, dynamic> json) {
    final refsRaw = (json['evidenceRefs'] as List<dynamic>?) ?? [];
    final bscRaw = (json['bscPerspectives'] as List<dynamic>?) ?? [];

    return SwotItemModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      strategicObjectiveId: json['strategicObjectiveId']?.toString() ?? '',
      itemType: SwotItemType.fromString(
        json['itemType']?.toString() ?? json['kind']?.toString() ?? json['category']?.toString(),
      ),
      content: json['content']?.toString() ?? json['statement']?.toString() ?? '',
      sourcePestelSignalId: json['sourcePestelSignalId']?.toString(),
      sourceResourceCapabilityId: json['sourceResourceCapabilityId']?.toString(),
      evidenceRefs: refsRaw.map((e) => e.toString()).toList(),
      bscPerspectives: bscRaw
          .map((p) => BscPerspective.fromString(p?.toString()))
          .where((p) => p != BscPerspective.unknown)
          .toList(),
      revision: json['revision'] is int ? json['revision'] as int : 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'strategicObjectiveId': strategicObjectiveId,
      'itemType': itemType.toApiString(),
      'content': content,
      'sourcePestelSignalId': sourcePestelSignalId,
      'sourceResourceCapabilityId': sourceResourceCapabilityId,
      'evidenceRefs': evidenceRefs,
      'bscPerspectives': bscPerspectives.map((p) => p.toApiString()).toList(),
      'revision': revision,
    };
  }
}

@immutable
class TowsOptionModel {
  final String id;
  final String workspaceId;
  final String strategicObjectiveId;
  final TowsOptionType optionType;
  final String title;
  final String? description;
  final List<String> swotLinkIds;
  final TowsOptionStatus status;
  final double? rankingScore;
  final double? impactScore;
  final double? difficultyScore;
  final String? evaluationNotes;
  final String? evaluatedByMemberId;
  final String? selectedAt;
  final String? decisionId;
  final int revision;

  const TowsOptionModel({
    required this.id,
    required this.workspaceId,
    required this.strategicObjectiveId,
    required this.optionType,
    required this.title,
    this.description,
    this.swotLinkIds = const [],
    required this.status,
    this.rankingScore,
    this.impactScore,
    this.difficultyScore,
    this.evaluationNotes,
    this.evaluatedByMemberId,
    this.selectedAt,
    this.decisionId,
    required this.revision,
  });

  factory TowsOptionModel.fromJson(Map<String, dynamic> json) {
    final linksRaw = (json['swotLinkIds'] as List<dynamic>?) ??
        (json['swotItemIds'] as List<dynamic>?) ??
        [];

    return TowsOptionModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      strategicObjectiveId: json['strategicObjectiveId']?.toString() ?? '',
      optionType: TowsOptionType.fromString(
        json['optionType']?.toString() ?? json['quadrant']?.toString(),
      ),
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? json['rationale']?.toString(),
      swotLinkIds: linksRaw.map((l) => l.toString()).toList(),
      status: TowsOptionStatus.fromString(json['status']?.toString()),
      rankingScore: (json['rankingScore'] is num) ? (json['rankingScore'] as num).toDouble() : null,
      impactScore: (json['impactScore'] is num) ? (json['impactScore'] as num).toDouble() : null,
      difficultyScore: (json['difficultyScore'] is num) ? (json['difficultyScore'] as num).toDouble() : null,
      evaluationNotes: json['evaluationNotes']?.toString(),
      evaluatedByMemberId: json['evaluatedByMemberId']?.toString(),
      selectedAt: json['selectedAt']?.toString(),
      decisionId: json['decisionId']?.toString(),
      revision: json['revision'] is int ? json['revision'] as int : 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'strategicObjectiveId': strategicObjectiveId,
      'optionType': optionType.toApiString(),
      'title': title,
      'description': description,
      'swotLinkIds': swotLinkIds,
      'status': status.toApiString(),
      'rankingScore': rankingScore,
      'impactScore': impactScore,
      'difficultyScore': difficultyScore,
      'evaluationNotes': evaluationNotes,
      'evaluatedByMemberId': evaluatedByMemberId,
      'selectedAt': selectedAt,
      'decisionId': decisionId,
      'revision': revision,
    };
  }
}

@immutable
class InitiativeModel {
  final String id;
  final String workspaceId;
  final String? projectId;
  final String title;
  final String status;
  final String approvalStatus;
  final String? strategicObjectiveId;
  final String? sourceTowsOptionId;
  final String? description;
  final String? intendedOutcome;
  final String? startDate;
  final String? targetDate;
  final String? ownerMemberId;
  final String? approvedByMemberId;
  final String? approvedAt;
  final String? approvalReason;
  final String? decisionId;
  final List<dynamic> milestones;
  final List<String> keyResultIds;
  final int? settingsRevision;
  final int revision;

  bool get isApproved => approvalStatus.toUpperCase() == 'APPROVED';
  bool get isDraft => approvalStatus.toUpperCase() == 'DRAFT';

  const InitiativeModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    required this.title,
    required this.status,
    required this.approvalStatus,
    this.strategicObjectiveId,
    this.sourceTowsOptionId,
    this.description,
    this.intendedOutcome,
    this.startDate,
    this.targetDate,
    this.ownerMemberId,
    this.approvedByMemberId,
    this.approvedAt,
    this.approvalReason,
    this.decisionId,
    this.milestones = const [],
    this.keyResultIds = const [],
    this.settingsRevision,
    required this.revision,
  });

  factory InitiativeModel.fromJson(Map<String, dynamic> json) {
    final krRaw = (json['keyResultIds'] as List<dynamic>?) ?? [];
    return InitiativeModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString(),
      title: json['title']?.toString() ?? '',
      status: json['status']?.toString() ?? 'active',
      approvalStatus: json['approvalStatus']?.toString() ?? 'DRAFT',
      strategicObjectiveId: json['strategicObjectiveId']?.toString(),
      sourceTowsOptionId: json['sourceTowsOptionId']?.toString(),
      description: json['description']?.toString(),
      intendedOutcome: json['intendedOutcome']?.toString(),
      startDate: json['startDate']?.toString(),
      targetDate: json['targetDate']?.toString(),
      ownerMemberId: json['ownerMemberId']?.toString(),
      approvedByMemberId: json['approvedByMemberId']?.toString(),
      approvedAt: json['approvedAt']?.toString(),
      approvalReason: json['approvalReason']?.toString() ?? json['reason']?.toString(),
      decisionId: json['decisionId']?.toString(),
      milestones: (json['milestones'] as List<dynamic>?) ?? const [],
      keyResultIds: krRaw.map((k) => k.toString()).toList(),
      settingsRevision: json['settingsRevision'] as int?,
      revision: json['revision'] is int ? json['revision'] as int : 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'projectId': projectId,
      'title': title,
      'status': status,
      'approvalStatus': approvalStatus,
      'strategicObjectiveId': strategicObjectiveId,
      'sourceTowsOptionId': sourceTowsOptionId,
      'description': description,
      'intendedOutcome': intendedOutcome,
      'startDate': startDate,
      'targetDate': targetDate,
      'ownerMemberId': ownerMemberId,
      'approvedByMemberId': approvedByMemberId,
      'approvedAt': approvedAt,
      'approvalReason': approvalReason,
      'decisionId': decisionId,
      'milestones': milestones,
      'keyResultIds': keyResultIds,
      'settingsRevision': settingsRevision,
      'revision': revision,
    };
  }
}

@immutable
class CycleReviewModel {
  final String id;
  final String workspaceId;
  final String? projectId;
  final String cycleId;
  final CycleReviewKind kind;
  final int scheduledWeekNo;
  final String? scheduledAt;
  final CycleReviewStatus status;
  final List<dynamic> krSnapshots;
  final List<dynamic> initiativeSnapshots;
  final List<dynamic> pestelSnapshots;
  final String? decisionId;
  final String? conclusion;
  final String? conductedByMemberId;
  final String? conductedAt;
  final int? settingsRevision;
  final int revision;
  final bool canEdit;
  final bool canClose;
  final bool canStart;

  const CycleReviewModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    required this.cycleId,
    required this.kind,
    required this.scheduledWeekNo,
    this.scheduledAt,
    required this.status,
    this.krSnapshots = const [],
    this.initiativeSnapshots = const [],
    this.pestelSnapshots = const [],
    this.decisionId,
    this.conclusion,
    this.conductedByMemberId,
    this.conductedAt,
    this.settingsRevision,
    required this.revision,
    this.canEdit = true,
    this.canClose = true,
    this.canStart = true,
  });

  factory CycleReviewModel.fromJson(Map<String, dynamic> json) {
    final status = CycleReviewStatus.fromString(json['status']?.toString());
    final canEditVal = json['canEdit'] is bool
        ? json['canEdit'] as bool
        : (status != CycleReviewStatus.completed && status != CycleReviewStatus.superseded);
    final canCloseVal = json['canClose'] is bool
        ? json['canClose'] as bool
        : (status == CycleReviewStatus.inProgress);
    final canStartVal = json['canStart'] is bool
        ? json['canStart'] as bool
        : (status == CycleReviewStatus.scheduled);

    return CycleReviewModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString(),
      cycleId: json['cycleId']?.toString() ?? '',
      kind: CycleReviewKind.fromString(json['kind']?.toString()),
      scheduledWeekNo: json['scheduledWeekNo'] is int ? json['scheduledWeekNo'] as int : 1,
      scheduledAt: json['scheduledAt']?.toString(),
      status: status,
      krSnapshots: (json['krSnapshots'] as List<dynamic>?) ?? const [],
      initiativeSnapshots: (json['initiativeSnapshots'] as List<dynamic>?) ?? const [],
      pestelSnapshots: (json['pestelSnapshots'] as List<dynamic>?) ?? const [],
      decisionId: json['decisionId']?.toString(),
      conclusion: json['conclusion']?.toString(),
      conductedByMemberId: json['conductedByMemberId']?.toString(),
      conductedAt: json['conductedAt']?.toString(),
      settingsRevision: json['settingsRevision'] as int?,
      revision: json['revision'] is int ? json['revision'] as int : 1,
      canEdit: canEditVal,
      canClose: canCloseVal,
      canStart: canStartVal,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'projectId': projectId,
      'cycleId': cycleId,
      'kind': kind.toApiString(),
      'scheduledWeekNo': scheduledWeekNo,
      'scheduledAt': scheduledAt,
      'status': status.toApiString(),
      'krSnapshots': krSnapshots,
      'initiativeSnapshots': initiativeSnapshots,
      'pestelSnapshots': pestelSnapshots,
      'decisionId': decisionId,
      'conclusion': conclusion,
      'conductedByMemberId': conductedByMemberId,
      'conductedAt': conductedAt,
      'settingsRevision': settingsRevision,
      'revision': revision,
      'canEdit': canEdit,
      'canClose': canClose,
      'canStart': canStart,
    };
  }
}

