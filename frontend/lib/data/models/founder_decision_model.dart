/// Founder Decision Model (F4 Specification).
/// 
/// Đại diện cho đối tượng quyết định chiến lược của Founder,
/// phân biệt với Approval tác vụ thông thường.
class FounderDecisionOptionModel {
  final String key;
  final String title;
  final String description;
  final String? financialImpact;
  final String? riskLevel;

  FounderDecisionOptionModel({
    required this.key,
    required this.title,
    required this.description,
    this.financialImpact,
    this.riskLevel,
  });

  factory FounderDecisionOptionModel.fromJson(Map<String, dynamic> json) {
    return FounderDecisionOptionModel(
      key: json['key'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      financialImpact: json['financial_impact'],
      riskLevel: json['risk_level'],
    );
  }

  Map<String, dynamic> toJson() => {
    'key': key,
    'title': title,
    'description': description,
    'financial_impact': financialImpact,
    'risk_level': riskLevel,
  };
}

class FounderDecisionModel {
  final int id;
  final int? workspaceId;
  final int? projectId;
  final String domain;
  final String question;
  final String? contextSummary;
  final List<FounderDecisionOptionModel> options;
  final Map<String, dynamic>? aiRecommendation;
  final List<String> evidenceIds;
  final Map<String, dynamic>? riskAnalysis;
  final String status; // PENDING | DECIDED | DISMISSED | DEFERRED
  final String? decisionMade;
  final String? founderNotes;
  final DateTime? decidedAt;
  final DateTime createdAt;

  FounderDecisionModel({
    required this.id,
    this.workspaceId,
    this.projectId,
    required this.domain,
    required this.question,
    this.contextSummary,
    this.options = const [],
    this.aiRecommendation,
    this.evidenceIds = const [],
    this.riskAnalysis,
    required this.status,
    this.decisionMade,
    this.founderNotes,
    this.decidedAt,
    required this.createdAt,
  });

  factory FounderDecisionModel.fromJson(Map<String, dynamic> json) {
    var rawOptions = json['options_jsonb'] as List? ?? [];
    return FounderDecisionModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      workspaceId: json['workspace_id'],
      projectId: json['project_id'],
      domain: json['domain'] ?? 'STRATEGY',
      question: json['question'] ?? '',
      contextSummary: json['context_summary'],
      options: rawOptions.map((e) => FounderDecisionOptionModel.fromJson(e as Map<String, dynamic>)).toList(),
      aiRecommendation: json['ai_recommendation_jsonb'],
      evidenceIds: (json['evidence_ids'] as List? ?? []).map((e) => e.toString()).toList(),
      riskAnalysis: json['risk_analysis_jsonb'],
      status: json['status'] ?? 'PENDING',
      decisionMade: json['decision_made'],
      founderNotes: json['founder_notes'],
      decidedAt: json['decided_at'] != null ? DateTime.tryParse(json['decided_at']) : null,
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : DateTime.now(),
    );
  }
}
