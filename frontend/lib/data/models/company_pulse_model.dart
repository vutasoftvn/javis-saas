/// Company Pulse & Next Best Action Models (F4 Specification).
library;

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
    final candidate = json['candidate'] as Map<String, dynamic>?;
    final title = json['title'] ?? candidate?['title'] ?? json['recommendation'] ?? '';
    final source = candidate?['source'] ?? json['category'];
    String category = 'FOUNDER_ACTION';
    if (source == 'assumption') {
      category = 'EXPERIMENT';
    } else if (source == 'task') {
      category = 'MISSION';
    } else if (source == 'okr_gap') {
      category = 'FOUNDER_ACTION';
    } else if (json['category'] != null) {
      category = json['category'];
    }

    return NextBestActionModel(
      id: json['id']?.toString() ?? candidate?['refId']?.toString() ?? '',
      category: category,
      title: title.toString(),
      rationale: json['rationale'] ?? json['decisionReason'] ?? 'Tập trung xác thực các giả định quan trọng nhất của giai đoạn P1 (Problem Validation).',
      urgency: json['urgency'] ?? 'HIGH',
      domain: json['domain'] ?? 'STRATEGY',
      actionPayload: json['action_payload'] ?? json['contextSnapshot'],
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
  // G3 Phase 1D (Stage Operating Engine): giá trị thật của Workspace.company_stage,
  // tự đổi theo StageGateService.apply_stage_advancement - null khi backend cũ
  // chưa trả field này hoặc workspace chưa xác định được.
  final String? companyStage;
  final String suggestedFocus;
  final DateTime updatedAt;

  CompanyPulseModel({
    this.goalsOnTrack = 0,
    this.totalActiveGoals = 0,
    this.activeMissions = 0,
    this.needsDecisionCount = 0,
    this.pendingApprovalsCount = 0,
    this.majorRisksCount = 0,
    this.companyStage,
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
      companyStage: json['company_stage'],
      suggestedFocus: json['suggested_focus'] ?? 'Tập trung kiểm chứng bài toán khách hàng.',
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : DateTime.now(),
    );
  }
}
