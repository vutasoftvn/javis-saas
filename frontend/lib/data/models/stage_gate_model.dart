import 'package:flutter/material.dart';

enum AuditStatus {
  approved,
  conditionallyApproved,
  rejected;

  static AuditStatus fromString(String? val) {
    if (val == null) return AuditStatus.rejected;
    final upper = val.toUpperCase();
    if (upper == 'APPROVED') return AuditStatus.approved;
    if (upper == 'CONDITIONALLY_APPROVED') return AuditStatus.conditionallyApproved;
    return AuditStatus.rejected;
  }

  String get labelVi {
    switch (this) {
      case AuditStatus.approved:
        return 'Đủ Điều Kiện Nâng Cấp (Approved)';
      case AuditStatus.conditionallyApproved:
        return 'Đạt Có Điều Kiện (Conditional)';
      case AuditStatus.rejected:
        return 'Chưa Đạt Chuẩn (Rejected)';
    }
  }

  Color get color {
    switch (this) {
      case AuditStatus.approved:
        return const Color(0xFF10B981);
      case AuditStatus.conditionallyApproved:
        return const Color(0xFFF59E0B);
      case AuditStatus.rejected:
        return const Color(0xFFEF4444);
    }
  }

  IconData get icon {
    switch (this) {
      case AuditStatus.approved:
        return Icons.check_circle_outline;
      case AuditStatus.conditionallyApproved:
        return Icons.warning_amber_rounded;
      case AuditStatus.rejected:
        return Icons.cancel_outlined;
    }
  }
}

enum AlertSeverity {
  critical,
  warning,
  info;

  static AlertSeverity fromString(String? val) {
    if (val == null) return AlertSeverity.info;
    final upper = val.toUpperCase();
    if (upper == 'CRITICAL') return AlertSeverity.critical;
    if (upper == 'WARNING') return AlertSeverity.warning;
    return AlertSeverity.info;
  }

  Color get color {
    switch (this) {
      case AlertSeverity.critical:
        return const Color(0xFFEF4444);
      case AlertSeverity.warning:
        return const Color(0xFFF59E0B);
      case AlertSeverity.info:
        return const Color(0xFF38BDF8);
    }
  }

  IconData get icon {
    switch (this) {
      case AlertSeverity.critical:
        return Icons.dangerous_outlined;
      case AlertSeverity.warning:
        return Icons.warning_outlined;
      case AlertSeverity.info:
        return Icons.info_outline;
    }
  }
}

class StageGateCriteriaModel {
  final String id;
  final String title;
  final String description;
  final bool isMet;

  StageGateCriteriaModel({
    required this.id,
    required this.title,
    required this.description,
    required this.isMet,
  });

  factory StageGateCriteriaModel.fromJson(Map<String, dynamic> json) {
    return StageGateCriteriaModel(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      isMet: json['is_met'] == true,
    );
  }
}

class StageGateAuditModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final String fromStage;
  final String toStage;
  final double readinessScore;
  final AuditStatus auditStatus;
  final List<StageGateCriteriaModel> passedCriteria;
  final List<StageGateCriteriaModel> missingCriteria;
  final List<Map<String, dynamic>> detectedRisks;
  final String auditedByAgent;
  final String recommendationNote;
  final DateTime createdAt;

  StageGateAuditModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.fromStage,
    required this.toStage,
    required this.readinessScore,
    required this.auditStatus,
    required this.passedCriteria,
    required this.missingCriteria,
    required this.detectedRisks,
    required this.auditedByAgent,
    required this.recommendationNote,
    required this.createdAt,
  });

  factory StageGateAuditModel.fromJson(Map<String, dynamic> json) {
    final passedList = (json['passed_criteria'] as List? ?? [])
        .map((item) => StageGateCriteriaModel.fromJson(item as Map<String, dynamic>))
        .toList();

    final missingList = (json['missing_criteria'] as List? ?? [])
        .map((item) => StageGateCriteriaModel.fromJson(item as Map<String, dynamic>))
        .toList();

    final risksList = (json['detected_risks'] as List? ?? [])
        .map((item) => item as Map<String, dynamic>)
        .toList();

    return StageGateAuditModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      fromStage: json['from_stage']?.toString() ?? 'S1_PROBLEM_VALIDATION',
      toStage: json['to_stage']?.toString() ?? 'S2_SOLUTION_VALIDATION',
      readinessScore: (json['readiness_score'] as num?)?.toDouble() ?? 0.0,
      auditStatus: AuditStatus.fromString(json['audit_status']?.toString()),
      passedCriteria: passedList,
      missingCriteria: missingList,
      detectedRisks: risksList,
      auditedByAgent: json['audited_by_agent']?.toString() ?? 'Stage Gate Auditor Agent',
      recommendationNote: json['recommendation_note']?.toString() ?? '',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class PrematureAlertModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final String currentStage;
  final String ruleCode;
  final AlertSeverity severity;
  final String title;
  final String message;
  final bool isDismissed;
  final DateTime createdAt;

  PrematureAlertModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.currentStage,
    required this.ruleCode,
    required this.severity,
    required this.title,
    required this.message,
    required this.isDismissed,
    required this.createdAt,
  });

  factory PrematureAlertModel.fromJson(Map<String, dynamic> json) {
    return PrematureAlertModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      currentStage: json['current_stage']?.toString() ?? '',
      ruleCode: json['rule_code']?.toString() ?? '',
      severity: AlertSeverity.fromString(json['severity']?.toString()),
      title: json['title']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
      isDismissed: json['is_dismissed'] == true,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
