import 'package:flutter/material.dart';

enum ProjectStage {
  s0Explore,
  s1ProblemValidation,
  s2SolutionValidation,
  s3BusinessValidation,
  s4GoToMarket,
  s5OperateGrowth,
  s6ScaleGovern;

  String get code {
    switch (this) {
      case ProjectStage.s0Explore:
        return 'S0';
      case ProjectStage.s1ProblemValidation:
        return 'S1';
      case ProjectStage.s2SolutionValidation:
        return 'S2';
      case ProjectStage.s3BusinessValidation:
        return 'S3';
      case ProjectStage.s4GoToMarket:
        return 'S4';
      case ProjectStage.s5OperateGrowth:
        return 'S5';
      case ProjectStage.s6ScaleGovern:
        return 'S6';
    }
  }

  String get displayNameVi {
    switch (this) {
      case ProjectStage.s0Explore:
        return 'Khám phá & Đánh giá cơ hội';
      case ProjectStage.s1ProblemValidation:
        return 'Xác thực vấn đề (Problem validation)';
      case ProjectStage.s2SolutionValidation:
        return 'Xác thực giải pháp (Solution validation)';
      case ProjectStage.s3BusinessValidation:
        return 'Xác thực mô hình (Business validation)';
      case ProjectStage.s4GoToMarket:
        return 'Đưa ra thị trường (Go-to-market)';
      case ProjectStage.s5OperateGrowth:
        return 'Vận hành & Tăng trưởng (Operate & grow)';
      case ProjectStage.s6ScaleGovern:
        return 'Mở rộng & Quản trị (Scale & govern)';
    }
  }

  String get shortNameVi {
    switch (this) {
      case ProjectStage.s0Explore:
        return 'Khám phá cơ hội';
      case ProjectStage.s1ProblemValidation:
        return 'Xác thực nỗi đau';
      case ProjectStage.s2SolutionValidation:
        return 'Xác thực MVP/Giá';
      case ProjectStage.s3BusinessValidation:
        return 'Xác thực doanh thu';
      case ProjectStage.s4GoToMarket:
        return 'Go-To-Market';
      case ProjectStage.s5OperateGrowth:
        return 'Vận hành & Tăng trưởng';
      case ProjectStage.s6ScaleGovern:
        return 'Mở rộng & Quản trị';
    }
  }

  Color get primaryColor {
    switch (this) {
      case ProjectStage.s0Explore:
        return const Color(0xFF94A3B8); // Slate 400
      case ProjectStage.s1ProblemValidation:
        return const Color(0xFF6366F1); // Indigo 500
      case ProjectStage.s2SolutionValidation:
        return const Color(0xFFA855F7); // Purple 500
      case ProjectStage.s3BusinessValidation:
        return const Color(0xFFF59E0B); // Amber 500
      case ProjectStage.s4GoToMarket:
        return const Color(0xFF06B6D4); // Cyan 500
      case ProjectStage.s5OperateGrowth:
        return const Color(0xFF10B981); // Emerald 500
      case ProjectStage.s6ScaleGovern:
        return const Color(0xFFEF4444); // Red 500
    }
  }

  List<Color> get gradientColors {
    switch (this) {
      case ProjectStage.s0Explore:
        return [const Color(0xFF64748B), const Color(0xFF475569)];
      case ProjectStage.s1ProblemValidation:
        return [const Color(0xFF6366F1), const Color(0xFF4F46E5)];
      case ProjectStage.s2SolutionValidation:
        return [const Color(0xFFA855F7), const Color(0xFF7E22CE)];
      case ProjectStage.s3BusinessValidation:
        return [const Color(0xFFF59E0B), const Color(0xFFD97706)];
      case ProjectStage.s4GoToMarket:
        return [const Color(0xFF06B6D4), const Color(0xFF0891B2)];
      case ProjectStage.s5OperateGrowth:
        return [const Color(0xFF10B981), const Color(0xFF059669)];
      case ProjectStage.s6ScaleGovern:
        return [const Color(0xFFEF4444), const Color(0xFFDC2626)];
    }
  }

  IconData get icon {
    switch (this) {
      case ProjectStage.s0Explore:
        return Icons.explore_outlined;
      case ProjectStage.s1ProblemValidation:
        return Icons.psychology_outlined;
      case ProjectStage.s2SolutionValidation:
        return Icons.lightbulb_outlined;
      case ProjectStage.s3BusinessValidation:
        return Icons.monetization_on_outlined;
      case ProjectStage.s4GoToMarket:
        return Icons.campaign_outlined;
      case ProjectStage.s5OperateGrowth:
        return Icons.trending_up_outlined;
      case ProjectStage.s6ScaleGovern:
        return Icons.account_balance_outlined;
    }
  }

  static ProjectStage fromString(String? raw) {
    if (raw == null) return ProjectStage.s1ProblemValidation;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('S0') || clean.contains('EXPLORE')) return ProjectStage.s0Explore;
    if (clean.contains('S1') || clean.contains('PROBLEM')) return ProjectStage.s1ProblemValidation;
    if (clean.contains('S2') || clean.contains('SOLUTION')) return ProjectStage.s2SolutionValidation;
    if (clean.contains('S3') || clean.contains('BUSINESS')) return ProjectStage.s3BusinessValidation;
    if (clean.contains('S4') || clean.contains('MARKET') || clean.contains('GTM')) return ProjectStage.s4GoToMarket;
    if (clean.contains('S5') || clean.contains('OPERATE') || clean.contains('GROWTH')) return ProjectStage.s5OperateGrowth;
    if (clean.contains('S6') || clean.contains('SCALE') || clean.contains('GOVERN')) return ProjectStage.s6ScaleGovern;
    return ProjectStage.s1ProblemValidation;
  }

  String toServerString() {
    switch (this) {
      case ProjectStage.s0Explore:
        return 'S0_EXPLORE';
      case ProjectStage.s1ProblemValidation:
        return 'S1_PROBLEM_VALIDATION';
      case ProjectStage.s2SolutionValidation:
        return 'S2_SOLUTION_VALIDATION';
      case ProjectStage.s3BusinessValidation:
        return 'S3_BUSINESS_VALIDATION';
      case ProjectStage.s4GoToMarket:
        return 'S4_GO_TO_MARKET';
      case ProjectStage.s5OperateGrowth:
        return 'S5_OPERATE_GROWTH';
      case ProjectStage.s6ScaleGovern:
        return 'S6_SCALE_GOVERN';
    }
  }
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
      companyStage: json['company_stage'] ?? 'S5_OPERATE_GROWTH',
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
