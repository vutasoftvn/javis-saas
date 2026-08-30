import 'package:flutter/material.dart';

enum PestelDimension {
  political,
  economic,
  social,
  technological,
  environmental,
  legal;

  String get labelVi {
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
    }
  }

  IconData get icon {
    switch (this) {
      case PestelDimension.political:
        return Icons.account_balance_outlined;
      case PestelDimension.economic:
        return Icons.trending_up_outlined;
      case PestelDimension.social:
        return Icons.people_alt_outlined;
      case PestelDimension.technological:
        return Icons.memory_outlined;
      case PestelDimension.environmental:
        return Icons.eco_outlined;
      case PestelDimension.legal:
        return Icons.gavel_outlined;
    }
  }

  Color get color {
    switch (this) {
      case PestelDimension.political:
        return const Color(0xFFEF4444);
      case PestelDimension.economic:
        return const Color(0xFF10B981);
      case PestelDimension.social:
        return const Color(0xFFF59E0B);
      case PestelDimension.technological:
        return const Color(0xFF38BDF8);
      case PestelDimension.environmental:
        return const Color(0xFF22C55E);
      case PestelDimension.legal:
        return const Color(0xFFA855F7);
    }
  }

  static PestelDimension fromString(String? raw) {
    if (raw == null) return PestelDimension.economic;
    final clean = raw.toLowerCase().trim();
    if (clean.contains('politic')) return PestelDimension.political;
    if (clean.contains('soc')) return PestelDimension.social;
    if (clean.contains('tech')) return PestelDimension.technological;
    if (clean.contains('env')) return PestelDimension.environmental;
    if (clean.contains('leg')) return PestelDimension.legal;
    return PestelDimension.economic;
  }
}

enum SwotType {
  strength,
  weakness,
  opportunity,
  threat;

  String get labelVi {
    switch (this) {
      case SwotType.strength:
        return 'Điểm Mạnh (S)';
      case SwotType.weakness:
        return 'Điểm Yếu (W)';
      case SwotType.opportunity:
        return 'Cơ Hội (O)';
      case SwotType.threat:
        return 'Thách Thức (T)';
    }
  }

  Color get color {
    switch (this) {
      case SwotType.strength:
        return const Color(0xFF10B981);
      case SwotType.weakness:
        return const Color(0xFFEF4444);
      case SwotType.opportunity:
        return const Color(0xFF38BDF8);
      case SwotType.threat:
        return const Color(0xFFF59E0B);
    }
  }

  static SwotType fromString(String? raw) {
    if (raw == null) return SwotType.strength;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('WEAK')) return SwotType.weakness;
    if (clean.contains('OPP')) return SwotType.opportunity;
    if (clean.contains('THREAT')) return SwotType.threat;
    return SwotType.strength;
  }
}

enum TowsType {
  so,
  wo,
  st,
  wt;

  String get labelVi {
    switch (this) {
      case TowsType.so:
        return 'Chiến Lược SO (Tận Dụng Đột Phá)';
      case TowsType.wo:
        return 'Chiến Lược WO (Khắc Phục Nắm Bắt)';
      case TowsType.st:
        return 'Chiến Lược ST (Dùng Mạnh Hóa Giải)';
      case TowsType.wt:
        return 'Chiến Lược WT (Phòng Thủ Sinh Tồn)';
    }
  }

  Color get color {
    switch (this) {
      case TowsType.so:
        return const Color(0xFF10B981);
      case TowsType.wo:
        return const Color(0xFF38BDF8);
      case TowsType.st:
        return const Color(0xFFF59E0B);
      case TowsType.wt:
        return const Color(0xFFEF4444);
    }
  }

  static TowsType fromString(String? raw) {
    if (raw == null) return TowsType.so;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('WO')) return TowsType.wo;
    if (clean.contains('ST')) return TowsType.st;
    if (clean.contains('WT')) return TowsType.wt;
    return TowsType.so;
  }
}

enum BscPerspective {
  financial,
  customer,
  internalOperations,
  learningGrowth;

  String get labelVi {
    switch (this) {
      case BscPerspective.financial:
        return 'Tài Chính (Financial)';
      case BscPerspective.customer:
        return 'Khách Hàng (Customer)';
      case BscPerspective.internalOperations:
        return 'Vận Hành Nội Bộ (Internal Operations)';
      case BscPerspective.learningGrowth:
        return 'Năng Lực & Con Người (Learning & Growth)';
    }
  }

  IconData get icon {
    switch (this) {
      case BscPerspective.financial:
        return Icons.attach_money;
      case BscPerspective.customer:
        return Icons.sentiment_satisfied_alt_outlined;
      case BscPerspective.internalOperations:
        return Icons.settings_suggest_outlined;
      case BscPerspective.learningGrowth:
        return Icons.psychology_outlined;
    }
  }

  Color get color {
    switch (this) {
      case BscPerspective.financial:
        return const Color(0xFF10B981);
      case BscPerspective.customer:
        return const Color(0xFF38BDF8);
      case BscPerspective.internalOperations:
        return const Color(0xFF818CF8);
      case BscPerspective.learningGrowth:
        return const Color(0xFFA855F7);
    }
  }

  static BscPerspective fromString(String? raw) {
    if (raw == null) return BscPerspective.financial;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('CUST')) return BscPerspective.customer;
    if (clean.contains('INTERNAL') || clean.contains('OPERAT')) return BscPerspective.internalOperations;
    if (clean.contains('LEARN') || clean.contains('GROW')) return BscPerspective.learningGrowth;
    return BscPerspective.financial;
  }
}

class PestelSignalModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final PestelDimension dimension;
  final String signalTitle;
  final String description;
  final String impactLevel;
  final String timeHorizon;
  final int? resultingHypothesisId;
  final String stageCaptured;
  final DateTime createdAt;

  PestelSignalModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.dimension,
    required this.signalTitle,
    required this.description,
    required this.impactLevel,
    required this.timeHorizon,
    this.resultingHypothesisId,
    required this.stageCaptured,
    required this.createdAt,
  });

  factory PestelSignalModel.fromJson(Map<String, dynamic> json) {
    return PestelSignalModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      dimension: PestelDimension.fromString(json['dimension']?.toString()),
      signalTitle: json['signal_title'] ?? '',
      description: json['description'] ?? '',
      impactLevel: json['impact_level'] ?? 'medium',
      timeHorizon: json['time_horizon'] ?? 'medium_term',
      resultingHypothesisId: json['resulting_hypothesis_id'] != null
          ? int.tryParse(json['resulting_hypothesis_id'].toString())
          : null,
      stageCaptured: json['stage_captured'] ?? 'P0_DISCOVERY',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class SwotItemModel {
  final int id;
  final int workspaceId;
  final int? projectId;
  final SwotType category;
  final String statement;
  final double importance;
  final String evidenceStatus;
  final List<int> evidenceRefs;
  final int? pestelSignalRef;
  final DateTime createdAt;

  SwotItemModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    required this.category,
    required this.statement,
    required this.importance,
    required this.evidenceStatus,
    this.evidenceRefs = const [],
    this.pestelSignalRef,
    required this.createdAt,
  });

  factory SwotItemModel.fromJson(Map<String, dynamic> json) {
    return SwotItemModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: json['project_id'] != null
          ? int.tryParse(json['project_id'].toString())
          : null,
      category: SwotType.fromString(json['category']?.toString()),
      statement: json['statement'] ?? '',
      importance: (json['importance'] as num?)?.toDouble() ?? 0.5,
      evidenceStatus: json['evidence_status'] ?? 'unverified',
      evidenceRefs: (json['evidence_refs'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .where((e) => e > 0)
              .toList() ??
          [],
      pestelSignalRef: json['pestel_signal_ref'] != null
          ? int.tryParse(json['pestel_signal_ref'].toString())
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class TowsOptionModel {
  final int id;
  final int workspaceId;
  final int? projectId;
  final TowsType quadrant;
  final String title;
  final String? tradeoffs;
  final String expectedImpact;
  final String confidence;
  final String status;
  final List<int> linkedStrengthIds;
  final List<int> linkedWeaknessIds;
  final List<int> linkedOpportunityIds;
  final List<int> linkedThreatIds;
  final int? resultingHypothesisId;
  final List<Map<String, dynamic>> tactics12wy;
  final DateTime createdAt;

  TowsOptionModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    required this.quadrant,
    required this.title,
    this.tradeoffs,
    required this.expectedImpact,
    required this.confidence,
    required this.status,
    this.linkedStrengthIds = const [],
    this.linkedWeaknessIds = const [],
    this.linkedOpportunityIds = const [],
    this.linkedThreatIds = const [],
    this.resultingHypothesisId,
    this.tactics12wy = const [],
    required this.createdAt,
  });

  factory TowsOptionModel.fromJson(Map<String, dynamic> json) {
    return TowsOptionModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: json['project_id'] != null
          ? int.tryParse(json['project_id'].toString())
          : null,
      quadrant: TowsType.fromString(json['quadrant']?.toString()),
      title: json['title'] ?? '',
      tradeoffs: json['tradeoffs'],
      expectedImpact: json['expected_impact'] ?? 'high',
      confidence: json['confidence'] ?? 'medium',
      status: json['status'] ?? 'draft',
      linkedStrengthIds: (json['linked_strength_ids'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .where((e) => e > 0)
              .toList() ??
          [],
      linkedWeaknessIds: (json['linked_weakness_ids'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .where((e) => e > 0)
              .toList() ??
          [],
      linkedOpportunityIds: (json['linked_opportunity_ids'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .where((e) => e > 0)
              .toList() ??
          [],
      linkedThreatIds: (json['linked_threat_ids'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .where((e) => e > 0)
              .toList() ??
          [],
      resultingHypothesisId: json['resulting_hypothesis_id'] != null
          ? int.tryParse(json['resulting_hypothesis_id'].toString())
          : null,
      tactics12wy: (json['tactics_12wy'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          [],
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class BscGoalModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final BscPerspective perspective;
  final String objective;
  final String kpiName;
  final String targetValue;
  final String currentValue;
  final List<String> initiatives;
  final String status;
  final DateTime createdAt;

  BscGoalModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.perspective,
    required this.objective,
    required this.kpiName,
    required this.targetValue,
    required this.currentValue,
    this.initiatives = const [],
    required this.status,
    required this.createdAt,
  });

  factory BscGoalModel.fromJson(Map<String, dynamic> json) {
    return BscGoalModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      perspective: BscPerspective.fromString(json['perspective']?.toString()),
      objective: json['objective'] ?? '',
      kpiName: json['kpi_name'] ?? '',
      targetValue: json['target_value'] ?? '',
      currentValue: json['current_value'] ?? '0',
      initiatives: (json['initiatives'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      status: json['status'] ?? 'on_track',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class StageLensSummaryModel {
  final int projectId;
  final String projectStage;
  final bool isBscUnlocked;
  final List<PestelSignalModel> pestelSignals;
  final List<SwotItemModel> swotItems;
  final List<TowsOptionModel> towsOptions;
  final List<BscGoalModel> bscGoals;

  StageLensSummaryModel({
    required this.projectId,
    required this.projectStage,
    required this.isBscUnlocked,
    this.pestelSignals = const [],
    this.swotItems = const [],
    this.towsOptions = const [],
    this.bscGoals = const [],
  });

  factory StageLensSummaryModel.fromJson(Map<String, dynamic> json) {
    return StageLensSummaryModel(
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      projectStage: json['project_stage'] ?? 'P1_PROBLEM_VALIDATION',
      isBscUnlocked: json['is_bsc_unlocked'] == true,
      pestelSignals: (json['pestel_signals'] as List<dynamic>?)
              ?.map((e) => PestelSignalModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      swotItems: (json['swot_items'] as List<dynamic>?)
              ?.map((e) => SwotItemModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      towsOptions: (json['tows_options'] as List<dynamic>?)
              ?.map((e) => TowsOptionModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      bscGoals: (json['bsc_goals'] as List<dynamic>?)
              ?.map((e) => BscGoalModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
