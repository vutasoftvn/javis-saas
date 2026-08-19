/// Company Pulse & Next Best Action Models (F4 Specification).

class NextBestActionModel {
  final String id;
  final String category; // FOUNDER_ACTION | AGENT_ACTION | MISSION | DECISION | EXPERIMENT
  final String title;
  final String rationale;
  final String urgency; // HIGH | MEDIUM | LOW
  final String domain;
  final Map<String, dynamic>? actionPayload;

  NextBestActionModel({
    required this.id,
    required this.category,
    required this.title,
    required this.rationale,
    this.urgency = 'HIGH',
    this.domain = 'STRATEGY',
    this.actionPayload,
  });

  factory NextBestActionModel.fromJson(Map<String, dynamic> json) {
    return NextBestActionModel(
      id: json['id'] ?? '',
      category: json['category'] ?? 'FOUNDER_ACTION',
      title: json['title'] ?? '',
      rationale: json['rationale'] ?? '',
      urgency: json['urgency'] ?? 'HIGH',
      domain: json['domain'] ?? 'STRATEGY',
      actionPayload: json['action_payload'],
    );
  }
}

class CompanyPulseModel {
  final int goalsOnTrack;
  final int totalActiveGoals;
  final int activeMissions;
  final int needsDecisionCount;
  final int pendingApprovalsCount;
  final int majorRisksCount;
  final String suggestedFocus;
  final DateTime updatedAt;

  CompanyPulseModel({
    this.goalsOnTrack = 0,
    this.totalActiveGoals = 0,
    this.activeMissions = 0,
    this.needsDecisionCount = 0,
    this.pendingApprovalsCount = 0,
    this.majorRisksCount = 0,
    this.suggestedFocus = 'Tập trung kiểm chứng bài toán khách hàng và hoàn thiện chiến thuật tuần.',
    required this.updatedAt,
  });

  factory CompanyPulseModel.fromJson(Map<String, dynamic> json) {
    return CompanyPulseModel(
      goalsOnTrack: json['goals_on_track'] ?? 0,
      totalActiveGoals: json['total_active_goals'] ?? 0,
      activeMissions: json['active_missions'] ?? 0,
      needsDecisionCount: json['needs_decision_count'] ?? 0,
      pendingApprovalsCount: json['pending_approvals_count'] ?? 0,
      majorRisksCount: json['major_risks_count'] ?? 0,
      suggestedFocus: json['suggested_focus'] ?? 'Tập trung kiểm chứng bài toán khách hàng.',
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : DateTime.now(),
    );
  }
}
