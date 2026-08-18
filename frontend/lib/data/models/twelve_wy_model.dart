import 'package:flutter/material.dart';

class TacticalItemModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int cycleId;
  final int weekNumber;
  final String title;
  final String description;
  final int? towsOptionId;
  final int? hypothesisId;
  final String leadIndicatorName;
  final int targetCount;
  final int actualCount;
  final String status; // PLANNED | IN_PROGRESS | DONE | BLOCKED
  final String ownerRole;
  final DateTime? completedAt;
  final DateTime createdAt;

  TacticalItemModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.cycleId,
    required this.weekNumber,
    required this.title,
    required this.description,
    this.towsOptionId,
    this.hypothesisId,
    required this.leadIndicatorName,
    required this.targetCount,
    required this.actualCount,
    required this.status,
    required this.ownerRole,
    this.completedAt,
    required this.createdAt,
  });

  bool get isDone => status.toUpperCase() == 'DONE' || actualCount >= targetCount;

  double get progressRatio => targetCount > 0 ? (actualCount / targetCount).clamp(0.0, 1.0) : 0.0;

  Color get statusColor {
    if (isDone) return const Color(0xFF10B981);
    if (status.toUpperCase() == 'IN_PROGRESS') return const Color(0xFF38BDF8);
    if (status.toUpperCase() == 'BLOCKED') return const Color(0xFFEF4444);
    return Colors.white60;
  }

  factory TacticalItemModel.fromJson(Map<String, dynamic> json) {
    return TacticalItemModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      cycleId: int.tryParse(json['cycle_id']?.toString() ?? '') ?? 0,
      weekNumber: int.tryParse(json['week_number']?.toString() ?? '') ?? 1,
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      towsOptionId: json['tows_option_id'] != null ? int.tryParse(json['tows_option_id'].toString()) : null,
      hypothesisId: json['hypothesis_id'] != null ? int.tryParse(json['hypothesis_id'].toString()) : null,
      leadIndicatorName: json['lead_indicator_name']?.toString() ?? 'Lead Indicator',
      targetCount: int.tryParse(json['target_count']?.toString() ?? '') ?? 1,
      actualCount: int.tryParse(json['actual_count']?.toString() ?? '') ?? 0,
      status: json['status']?.toString() ?? 'PLANNED',
      ownerRole: json['owner_role']?.toString() ?? 'Founder',
      completedAt: json['completed_at'] != null ? DateTime.tryParse(json['completed_at'].toString()) : null,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now() : DateTime.now(),
    );
  }
}

class TwelveWeekCycleModel {
  final int id;
  final int workspaceId;
  final int? projectId;
  final String title;
  final String visionStatement;
  final String stageAtStart;
  final int currentWeek;
  final int totalWeeks;
  final String status;
  final double overallExecutionScore;
  final DateTime? startDate;
  final DateTime? endDate;
  final DateTime createdAt;

  TwelveWeekCycleModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    required this.title,
    required this.visionStatement,
    required this.stageAtStart,
    required this.currentWeek,
    required this.totalWeeks,
    required this.status,
    required this.overallExecutionScore,
    this.startDate,
    this.endDate,
    required this.createdAt,
  });

  factory TwelveWeekCycleModel.fromJson(Map<String, dynamic> json) {
    return TwelveWeekCycleModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: json['project_id'] != null ? int.tryParse(json['project_id'].toString()) : null,
      title: json['title']?.toString() ?? json['theme']?.toString() ?? 'Chu Kỳ 12 Tuần',
      visionStatement: json['vision_statement']?.toString() ?? '',
      stageAtStart: json['stage_at_start']?.toString() ?? 'S1_PROBLEM_VALIDATION',
      currentWeek: int.tryParse(json['current_week']?.toString() ?? '') ?? 1,
      totalWeeks: int.tryParse(json['total_weeks']?.toString() ?? json['duration_weeks']?.toString() ?? '') ?? 12,
      status: json['status']?.toString() ?? 'ACTIVE',
      overallExecutionScore: (json['overall_execution_score'] as num?)?.toDouble() ?? 0.0,
      startDate: json['start_date'] != null ? DateTime.tryParse(json['start_date'].toString()) : null,
      endDate: json['end_date'] != null ? DateTime.tryParse(json['end_date'].toString()) : null,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now() : DateTime.now(),
    );
  }
}

class WeeklyReviewModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int cycleId;
  final int weekNumber;
  final double executionScore;
  final int totalPlanned;
  final int totalCompleted;
  final List<String> keyBreakthroughs;
  final List<String> rootCauseBlocks;
  final List<String> aiRecommendations;
  final DateTime createdAt;

  WeeklyReviewModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.cycleId,
    required this.weekNumber,
    required this.executionScore,
    required this.totalPlanned,
    required this.totalCompleted,
    required this.keyBreakthroughs,
    required this.rootCauseBlocks,
    required this.aiRecommendations,
    required this.createdAt,
  });

  factory WeeklyReviewModel.fromJson(Map<String, dynamic> json) {
    return WeeklyReviewModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      cycleId: int.tryParse(json['cycle_id']?.toString() ?? '') ?? 0,
      weekNumber: int.tryParse(json['week_number']?.toString() ?? '') ?? 1,
      executionScore: (json['execution_score'] as num?)?.toDouble() ?? 0.0,
      totalPlanned: int.tryParse(json['total_planned']?.toString() ?? '') ?? 0,
      totalCompleted: int.tryParse(json['total_completed']?.toString() ?? '') ?? 0,
      keyBreakthroughs: (json['key_breakthroughs'] as List? ?? []).map((e) => e.toString()).toList(),
      rootCauseBlocks: (json['root_cause_blocks'] as List? ?? []).map((e) => e.toString()).toList(),
      aiRecommendations: (json['ai_recommendations'] as List? ?? []).map((e) => e.toString()).toList(),
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now() : DateTime.now(),
    );
  }
}

class TwelveWyDashboardModel {
  final TwelveWeekCycleModel cycle;
  final int currentWeek;
  final double currentWeekExecutionScore;
  final Map<int, List<TacticalItemModel>> tacticsByWeek;
  final Map<int, double> weeklyScores;
  final WeeklyReviewModel? latestReview;

  TwelveWyDashboardModel({
    required this.cycle,
    required this.currentWeek,
    required this.currentWeekExecutionScore,
    required this.tacticsByWeek,
    required this.weeklyScores,
    this.latestReview,
  });

  factory TwelveWyDashboardModel.fromJson(Map<String, dynamic> json) {
    final cycleData = json['cycle'] as Map<String, dynamic>? ?? {};
    final cycle = TwelveWeekCycleModel.fromJson(cycleData);

    final rawTactics = json['tactics_by_week'] as Map<String, dynamic>? ?? {};
    final tacticsMap = <int, List<TacticalItemModel>>{};
    rawTactics.forEach((k, v) {
      final weekNo = int.tryParse(k) ?? 1;
      final list = (v as List? ?? [])
          .map((item) => TacticalItemModel.fromJson(item as Map<String, dynamic>))
          .toList();
      tacticsMap[weekNo] = list;
    });

    final rawScores = json['weekly_scores'] as Map<String, dynamic>? ?? {};
    final scoresMap = <int, double>{};
    rawScores.forEach((k, v) {
      final weekNo = int.tryParse(k) ?? 1;
      scoresMap[weekNo] = (v as num?)?.toDouble() ?? 0.0;
    });

    final reviewData = json['latest_review'] as Map<String, dynamic>?;

    return TwelveWyDashboardModel(
      cycle: cycle,
      currentWeek: int.tryParse(json['current_week']?.toString() ?? '') ?? 1,
      currentWeekExecutionScore: (json['current_week_execution_score'] as num?)?.toDouble() ?? 0.0,
      tacticsByWeek: tacticsMap,
      weeklyScores: scoresMap,
      latestReview: reviewData != null ? WeeklyReviewModel.fromJson(reviewData) : null,
    );
  }
}
