import 'package:flutter/material.dart';

enum ProjectStage {
  p0Discovery,
  p1ProblemValidation,
  p2SolutionValidation,
  p3BuildValidate,
  p4GoToMarket,
  p5OperateGrowth,
  p6ScaleGovern;

  String get code {
    switch (this) {
      case ProjectStage.p0Discovery:
        return 'P0';
      case ProjectStage.p1ProblemValidation:
        return 'P1';
      case ProjectStage.p2SolutionValidation:
        return 'P2';
      case ProjectStage.p3BuildValidate:
        return 'P3';
      case ProjectStage.p4GoToMarket:
        return 'P4';
      case ProjectStage.p5OperateGrowth:
        return 'P5';
      case ProjectStage.p6ScaleGovern:
        return 'P6';
    }
  }

  String get wireValue {
    switch (this) {
      case ProjectStage.p0Discovery:
        return 'P0_DISCOVERY';
      case ProjectStage.p1ProblemValidation:
        return 'P1_PROBLEM_VALIDATION';
      case ProjectStage.p2SolutionValidation:
        return 'P2_SOLUTION_VALIDATION';
      case ProjectStage.p3BuildValidate:
        return 'P3_BUILD_VALIDATE';
      case ProjectStage.p4GoToMarket:
        return 'P4_GO_TO_MARKET';
      case ProjectStage.p5OperateGrowth:
        return 'P5_OPERATE_GROWTH';
      case ProjectStage.p6ScaleGovern:
        return 'P6_SCALE_GOVERN';
    }
  }

  String get displayNameVi {
    switch (this) {
      case ProjectStage.p0Discovery:
        return 'Khám phá & Đánh giá cơ hội';
      case ProjectStage.p1ProblemValidation:
        return 'Xác thực vấn đề (Problem validation)';
      case ProjectStage.p2SolutionValidation:
        return 'Xác thực giải pháp (Solution validation)';
      case ProjectStage.p3BuildValidate:
        return 'Xây dựng & Thử nghiệm (Build & validate)';
      case ProjectStage.p4GoToMarket:
        return 'Đưa ra thị trường (Go-to-market)';
      case ProjectStage.p5OperateGrowth:
        return 'Vận hành & Tăng trưởng (Operate & grow)';
      case ProjectStage.p6ScaleGovern:
        return 'Mở rộng & Quản trị (Scale & govern)';
    }
  }

  String get shortNameVi {
    switch (this) {
      case ProjectStage.p0Discovery:
        return 'Khám phá cơ hội';
      case ProjectStage.p1ProblemValidation:
        return 'Xác thực nỗi đau';
      case ProjectStage.p2SolutionValidation:
        return 'Xác thực MVP/Giá';
      case ProjectStage.p3BuildValidate:
        return 'Xây dựng & Thử nghiệm';
      case ProjectStage.p4GoToMarket:
        return 'Go-To-Market';
      case ProjectStage.p5OperateGrowth:
        return 'Vận hành & Tăng trưởng';
      case ProjectStage.p6ScaleGovern:
        return 'Mở rộng & Quản trị';
    }
  }

  Color get primaryColor {
    switch (this) {
      case ProjectStage.p0Discovery:
        return const Color(0xFF94A3B8); // Slate 400
      case ProjectStage.p1ProblemValidation:
        return const Color(0xFF6366F1); // Indigo 500
      case ProjectStage.p2SolutionValidation:
        return const Color(0xFFA855F7); // Purple 500
      case ProjectStage.p3BuildValidate:
        return const Color(0xFFF59E0B); // Amber 500
      case ProjectStage.p4GoToMarket:
        return const Color(0xFF06B6D4); // Cyan 500
      case ProjectStage.p5OperateGrowth:
        return const Color(0xFF10B981); // Emerald 500
      case ProjectStage.p6ScaleGovern:
        return const Color(0xFFEF4444); // Red 500
    }
  }

  List<Color> get gradientColors {
    switch (this) {
      case ProjectStage.p0Discovery:
        return [const Color(0xFF64748B), const Color(0xFF475569)];
      case ProjectStage.p1ProblemValidation:
        return [const Color(0xFF6366F1), const Color(0xFF4F46E5)];
      case ProjectStage.p2SolutionValidation:
        return [const Color(0xFFA855F7), const Color(0xFF7E22CE)];
      case ProjectStage.p3BuildValidate:
        return [const Color(0xFFF59E0B), const Color(0xFFD97706)];
      case ProjectStage.p4GoToMarket:
        return [const Color(0xFF06B6D4), const Color(0xFF0891B2)];
      case ProjectStage.p5OperateGrowth:
        return [const Color(0xFF10B981), const Color(0xFF059669)];
      case ProjectStage.p6ScaleGovern:
        return [const Color(0xFFEF4444), const Color(0xFFDC2626)];
    }
  }

  IconData get icon {
    switch (this) {
      case ProjectStage.p0Discovery:
        return Icons.explore_outlined;
      case ProjectStage.p1ProblemValidation:
        return Icons.psychology_outlined;
      case ProjectStage.p2SolutionValidation:
        return Icons.lightbulb_outlined;
      case ProjectStage.p3BuildValidate:
        return Icons.monetization_on_outlined;
      case ProjectStage.p4GoToMarket:
        return Icons.campaign_outlined;
      case ProjectStage.p5OperateGrowth:
        return Icons.trending_up_outlined;
      case ProjectStage.p6ScaleGovern:
        return Icons.account_balance_outlined;
    }
  }

  static ProjectStage? tryFromWire(String? raw) {
    if (raw == null) return null;
    for (final s in values) {
      if (s.wireValue == raw) return s;
    }
    return null;
  }

  static ProjectStage fromString(String? raw) {
    final matched = tryFromWire(raw);
    if (matched != null) return matched;
    if (raw == null) return ProjectStage.p1ProblemValidation;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('P0') || clean.contains('DISCOVERY')) return ProjectStage.p0Discovery;
    if (clean.contains('P1') || clean.contains('PROBLEM')) return ProjectStage.p1ProblemValidation;
    if (clean.contains('P2') || clean.contains('SOLUTION')) return ProjectStage.p2SolutionValidation;
    if (clean.contains('P3') || clean.contains('BUILD')) return ProjectStage.p3BuildValidate;
    if (clean.contains('P4') || clean.contains('MARKET') || clean.contains('GTM')) return ProjectStage.p4GoToMarket;
    if (clean.contains('P5') || clean.contains('OPERATE') || clean.contains('GROWTH')) return ProjectStage.p5OperateGrowth;
    if (clean.contains('P6') || clean.contains('SCALE') || clean.contains('GOVERN')) return ProjectStage.p6ScaleGovern;
    return ProjectStage.p1ProblemValidation;
  }

  String toServerString() => wireValue;
}

class StagePolicyModel {
  final ProjectStage stage;
  final String stageNameVi;
  final String code;
  final String primaryGoal;
  final List<String> primaryQuestions;
  final List<String> requiredEntities;
  final List<String> primaryMetrics;
  final List<String> deemphasizedTools;
  final List<String> recommendedMethods;
  final List<String> optionalLenses;
  final List<String> priorityAgents;
  final String reviewCadence;

  StagePolicyModel({
    required this.stage,
    required this.stageNameVi,
    required this.code,
    required this.primaryGoal,
    required this.primaryQuestions,
    required this.requiredEntities,
    required this.primaryMetrics,
    required this.deemphasizedTools,
    required this.recommendedMethods,
    required this.optionalLenses,
    required this.priorityAgents,
    required this.reviewCadence,
  });

  factory StagePolicyModel.fromJson(Map<String, dynamic> json) {
    return StagePolicyModel(
      stage: ProjectStage.fromString(json['stage']),
      stageNameVi: json['stage_name_vi'] ?? '',
      code: json['code'] ?? '',
      primaryGoal: json['primary_goal'] ?? '',
      primaryQuestions: List<String>.from(json['primary_questions'] ?? []),
      requiredEntities: List<String>.from(json['required_entities'] ?? []),
      primaryMetrics: List<String>.from(json['primary_metrics'] ?? []),
      deemphasizedTools: List<String>.from(json['deemphasized_tools'] ?? []),
      recommendedMethods: List<String>.from(json['recommended_methods'] ?? []),
      optionalLenses: List<String>.from(json['optional_lenses'] ?? []),
      priorityAgents: List<String>.from(json['priority_agents'] ?? []),
      reviewCadence: json['review_cadence'] ?? 'weekly',
    );
  }
}

class StageContextModel {
  final int workspaceId;
  final String companyStage;
  final String? companyVision;
  final String? companyMission;
  final List<String> companyValues;

  final int? projectId;
  final String? projectTitle;
  final String? projectType;
  final ProjectStage projectStage;
  final DateTime? stageStartedAt;
  final String? stageGoal;
  final List<String> criticalConstraints;
  final Map<String, dynamic> exitCriteria;
  final Map<String, dynamic> stageMetadata;
  final StagePolicyModel policy;

  StageContextModel({
    required this.workspaceId,
    required this.companyStage,
    this.companyVision,
    this.companyMission,
    required this.companyValues,
    this.projectId,
    this.projectTitle,
    this.projectType,
    required this.projectStage,
    this.stageStartedAt,
    this.stageGoal,
    required this.criticalConstraints,
    required this.exitCriteria,
    required this.stageMetadata,
    required this.policy,
  });

  factory StageContextModel.fromJson(Map<String, dynamic> json) {
    return StageContextModel(
      workspaceId: json['workspace_id'] ?? 0,
      companyStage: json['company_stage'] ?? 'P5_OPERATE_GROWTH',
      companyVision: json['company_vision'],
      companyMission: json['company_mission'],
      companyValues: List<String>.from(json['company_values'] ?? []),
      projectId: json['project_id'],
      projectTitle: json['project_title'],
      projectType: json['project_type'],
      projectStage: ProjectStage.fromString(json['project_stage']),
      stageStartedAt: json['stage_started_at'] != null
          ? DateTime.tryParse(json['stage_started_at'])
          : null,
      stageGoal: json['stage_goal'],
      criticalConstraints: List<String>.from(json['critical_constraints'] ?? []),
      exitCriteria: Map<String, dynamic>.from(json['exit_criteria'] ?? {}),
      stageMetadata: Map<String, dynamic>.from(json['stage_metadata'] ?? {}),
      policy: StagePolicyModel.fromJson(json['policy'] ?? {}),
    );
  }
}
