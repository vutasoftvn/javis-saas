import 'package:flutter/material.dart';

enum EvidenceLadderLevel {
  e0Opinion,
  e1StatedInterest,
  e2ObservedProblem,
  e3BehavioralCommitment,
  e4EconomicCommitment,
  e5RepeatBehavior,
  e6ScalableEvidence;

  String get code {
    switch (this) {
      case EvidenceLadderLevel.e0Opinion:
        return 'E0';
      case EvidenceLadderLevel.e1StatedInterest:
        return 'E1';
      case EvidenceLadderLevel.e2ObservedProblem:
        return 'E2';
      case EvidenceLadderLevel.e3BehavioralCommitment:
        return 'E3';
      case EvidenceLadderLevel.e4EconomicCommitment:
        return 'E4';
      case EvidenceLadderLevel.e5RepeatBehavior:
        return 'E5';
      case EvidenceLadderLevel.e6ScalableEvidence:
        return 'E6';
    }
  }

  String get titleVi {
    switch (this) {
      case EvidenceLadderLevel.e0Opinion:
        return 'E0: Ý kiến / Cảm tính';
      case EvidenceLadderLevel.e1StatedInterest:
        return 'E1: Khách nói thích';
      case EvidenceLadderLevel.e2ObservedProblem:
        return 'E2: Nỗi đau quan sát được';
      case EvidenceLadderLevel.e3BehavioralCommitment:
        return 'E3: Cam kết hành vi / Thời gian';
      case EvidenceLadderLevel.e4EconomicCommitment:
        return 'E4: Trả tiền thật / Đặt cọc Pilot';
      case EvidenceLadderLevel.e5RepeatBehavior:
        return 'E5: Khách mua lại / Tái gia hạn';
      case EvidenceLadderLevel.e6ScalableEvidence:
        return 'E6: Dữ liệu tăng trưởng quy mô';
    }
  }

  String get shortLabelVi {
    switch (this) {
      case EvidenceLadderLevel.e0Opinion:
        return 'Ý kiến';
      case EvidenceLadderLevel.e1StatedInterest:
        return 'Nói thích';
      case EvidenceLadderLevel.e2ObservedProblem:
        return 'Nỗi đau thật';
      case EvidenceLadderLevel.e3BehavioralCommitment:
        return 'Dành thời gian';
      case EvidenceLadderLevel.e4EconomicCommitment:
        return 'Trả tiền';
      case EvidenceLadderLevel.e5RepeatBehavior:
        return 'Mua lại';
      case EvidenceLadderLevel.e6ScalableEvidence:
        return 'Dữ liệu lớn';
    }
  }

  double get weight {
    switch (this) {
      case EvidenceLadderLevel.e0Opinion:
        return 0.0;
      case EvidenceLadderLevel.e1StatedInterest:
        return 0.2;
      case EvidenceLadderLevel.e2ObservedProblem:
        return 0.4;
      case EvidenceLadderLevel.e3BehavioralCommitment:
        return 0.7;
      case EvidenceLadderLevel.e4EconomicCommitment:
        return 0.9;
      case EvidenceLadderLevel.e5RepeatBehavior:
        return 0.95;
      case EvidenceLadderLevel.e6ScalableEvidence:
        return 1.0;
    }
  }

  Color get color {
    switch (this) {
      case EvidenceLadderLevel.e0Opinion:
        return const Color(0xFF94A3B8); // Slate
      case EvidenceLadderLevel.e1StatedInterest:
        return const Color(0xFF38BDF8); // Sky
      case EvidenceLadderLevel.e2ObservedProblem:
        return const Color(0xFF6366F1); // Indigo
      case EvidenceLadderLevel.e3BehavioralCommitment:
        return const Color(0xFFA855F7); // Purple
      case EvidenceLadderLevel.e4EconomicCommitment:
        return const Color(0xFF10B981); // Emerald
      case EvidenceLadderLevel.e5RepeatBehavior:
        return const Color(0xFF14B8A6); // Teal
      case EvidenceLadderLevel.e6ScalableEvidence:
        return const Color(0xFFF59E0B); // Amber
    }
  }

  static EvidenceLadderLevel fromString(String? raw) {
    if (raw == null) return EvidenceLadderLevel.e1StatedInterest;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('E0') || clean.contains('OPINION')) return EvidenceLadderLevel.e0Opinion;
    if (clean.contains('E1') || clean.contains('STATED')) return EvidenceLadderLevel.e1StatedInterest;
    if (clean.contains('E2') || clean.contains('OBSERVED')) return EvidenceLadderLevel.e2ObservedProblem;
    if (clean.contains('E3') || clean.contains('BEHAVIORAL')) return EvidenceLadderLevel.e3BehavioralCommitment;
    if (clean.contains('E4') || clean.contains('ECONOMIC')) return EvidenceLadderLevel.e4EconomicCommitment;
    if (clean.contains('E5') || clean.contains('REPEAT')) return EvidenceLadderLevel.e5RepeatBehavior;
    if (clean.contains('E6') || clean.contains('SCALABLE')) return EvidenceLadderLevel.e6ScalableEvidence;
    return EvidenceLadderLevel.e1StatedInterest;
  }

  String toServerString() {
    switch (this) {
      case EvidenceLadderLevel.e0Opinion:
        return 'E0_OPINION';
      case EvidenceLadderLevel.e1StatedInterest:
        return 'E1_STATED_INTEREST';
      case EvidenceLadderLevel.e2ObservedProblem:
        return 'E2_OBSERVED_PROBLEM';
      case EvidenceLadderLevel.e3BehavioralCommitment:
        return 'E3_BEHAVIORAL_COMMITMENT';
      case EvidenceLadderLevel.e4EconomicCommitment:
        return 'E4_ECONOMIC_COMMITMENT';
      case EvidenceLadderLevel.e5RepeatBehavior:
        return 'E5_REPEAT_BEHAVIOR';
      case EvidenceLadderLevel.e6ScalableEvidence:
        return 'E6_SCALABLE_EVIDENCE';
    }
  }
}

enum HypothesisStatus {
  untested,
  testing,
  supported,
  contradicted,
  invalidated;

  String get displayNameVi {
    switch (this) {
      case HypothesisStatus.untested:
        return 'Chưa kiểm chứng';
      case HypothesisStatus.testing:
        return 'Đang kiểm chứng';
      case HypothesisStatus.supported:
        return 'Đã xác thực (Passed)';
      case HypothesisStatus.contradicted:
        return 'Bị phủ định (Failed)';
      case HypothesisStatus.invalidated:
        return 'Không còn giá trị';
    }
  }

  Color get color {
    switch (this) {
      case HypothesisStatus.untested:
        return const Color(0xFF94A3B8);
      case HypothesisStatus.testing:
        return const Color(0xFF38BDF8);
      case HypothesisStatus.supported:
        return const Color(0xFF10B981);
      case HypothesisStatus.contradicted:
        return const Color(0xFFEF4444);
      case HypothesisStatus.invalidated:
        return const Color(0xFF64748B);
    }
  }

  static HypothesisStatus fromString(String? raw) {
    if (raw == null) return HypothesisStatus.untested;
    final clean = raw.toUpperCase().trim();
    if (clean.contains('TESTING')) return HypothesisStatus.testing;
    if (clean.contains('SUPPORTED')) return HypothesisStatus.supported;
    if (clean.contains('CONTRADICTED')) return HypothesisStatus.contradicted;
    if (clean.contains('INVALIDATED')) return HypothesisStatus.invalidated;
    return HypothesisStatus.untested;
  }
}

class HypothesisModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final String category;
  final String statement;
  final double importance;
  final double uncertainty;
  final double riskScore;
  final double evidenceScore;
  final double confidence;
  final HypothesisStatus status;
  final String stageCreated;
  final List<int> evidenceRefs;
  final List<int> experimentRefs;
  final String? nextAction;
  final DateTime createdAt;
  final DateTime updatedAt;

  HypothesisModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.category,
    required this.statement,
    required this.importance,
    required this.uncertainty,
    required this.riskScore,
    required this.evidenceScore,
    required this.confidence,
    required this.status,
    required this.stageCreated,
    required this.evidenceRefs,
    required this.experimentRefs,
    this.nextAction,
    required this.createdAt,
    required this.updatedAt,
  });

  factory HypothesisModel.fromJson(Map<String, dynamic> json) {
    return HypothesisModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      category: json['category'] ?? 'problem',
      statement: json['statement'] ?? '',
      importance: (json['importance'] as num?)?.toDouble() ?? 0.5,
      uncertainty: (json['uncertainty'] as num?)?.toDouble() ?? 0.5,
      riskScore: (json['risk_score'] as num?)?.toDouble() ?? 0.25,
      evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      status: HypothesisStatus.fromString(json['status']),
      stageCreated: json['stage_created'] ?? 'P1_PROBLEM_VALIDATION',
      evidenceRefs: (json['evidence_refs'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .toList() ??
          [],
      experimentRefs: (json['experiment_refs'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .toList() ??
          [],
      nextAction: json['next_action'],
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at']) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  bool get isCritical => (importance >= 0.7 && uncertainty >= 0.7) || riskScore >= 0.5;
}

class EvidenceModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final String type;
  final EvidenceLadderLevel ladderLevel;
  final double ladderWeight;
  final String source;
  final String claimSupported;
  final String strength;
  final String direction;
  final List<int> hypothesisRefs;
  final List<int> artifactRefs;
  final Map<String, dynamic> rawPayload;
  final DateTime capturedAt;
  final DateTime createdAt;

  EvidenceModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.type,
    required this.ladderLevel,
    required this.ladderWeight,
    required this.source,
    required this.claimSupported,
    required this.strength,
    required this.direction,
    required this.hypothesisRefs,
    required this.artifactRefs,
    required this.rawPayload,
    required this.capturedAt,
    required this.createdAt,
  });

  factory EvidenceModel.fromJson(Map<String, dynamic> json) {
    return EvidenceModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      type: json['type'] ?? 'interview',
      ladderLevel: EvidenceLadderLevel.fromString(json['ladder_level']),
      ladderWeight: (json['ladder_weight'] as num?)?.toDouble() ?? 0.2,
      source: json['source'] ?? '',
      claimSupported: json['claim_supported'] ?? '',
      strength: json['strength'] ?? 'medium',
      direction: json['direction'] ?? 'supports',
      hypothesisRefs: (json['hypothesis_refs'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .toList() ??
          [],
      artifactRefs: (json['artifact_refs'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .toList() ??
          [],
      rawPayload: Map<String, dynamic>.from(json['raw_payload'] ?? {}),
      capturedAt: json['captured_at'] != null
          ? DateTime.tryParse(json['captured_at']) ?? DateTime.now()
          : DateTime.now(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class StrategicDecisionModel {
  final int id;
  final int workspaceId;
  final int? projectId;
  final String? question;
  final String decision;
  final String? selectedOption;
  final List<String> alternatives;
  final String? rationale;
  final List<int> evidenceRefs;
  final String stage;
  final String? expectedResult;
  final DateTime? reviewDate;
  final String status;
  final int? decidedBy;
  final DateTime createdAt;

  StrategicDecisionModel({
    required this.id,
    required this.workspaceId,
    this.projectId,
    this.question,
    required this.decision,
    this.selectedOption,
    required this.alternatives,
    this.rationale,
    required this.evidenceRefs,
    required this.stage,
    this.expectedResult,
    this.reviewDate,
    required this.status,
    this.decidedBy,
    required this.createdAt,
  });

  factory StrategicDecisionModel.fromJson(Map<String, dynamic> json) {
    return StrategicDecisionModel(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      workspaceId: int.tryParse(json['workspace_id']?.toString() ?? '') ?? 0,
      projectId: json['project_id'] != null ? int.tryParse(json['project_id'].toString()) : null,
      question: json['question'],
      decision: json['decision'] ?? '',
      selectedOption: json['selected_option'],
      alternatives: List<String>.from(json['alternatives'] ?? []),
      rationale: json['rationale'],
      evidenceRefs: (json['evidence_refs'] as List<dynamic>?)
              ?.map((e) => int.tryParse(e.toString()) ?? 0)
              .toList() ??
          [],
      stage: json['stage'] ?? 'P1_PROBLEM_VALIDATION',
      expectedResult: json['expected_result'],
      reviewDate: json['review_date'] != null ? DateTime.tryParse(json['review_date']) : null,
      status: json['status'] ?? 'active',
      decidedBy: json['decided_by'] != null ? int.tryParse(json['decided_by'].toString()) : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class AssumptionMatrixModel {
  final int projectId;
  final int totalHypotheses;
  final int criticalCount;
  final List<HypothesisModel> criticalTestFirst;
  final List<HypothesisModel> monitor;
  final List<HypothesisModel> importantLowRisk;
  final List<HypothesisModel> lowPriority;

  AssumptionMatrixModel({
    required this.projectId,
    required this.totalHypotheses,
    required this.criticalCount,
    required this.criticalTestFirst,
    required this.monitor,
    required this.importantLowRisk,
    required this.lowPriority,
  });

  factory AssumptionMatrixModel.fromJson(Map<String, dynamic> json) {
    final quads = json['quadrants'] as Map<String, dynamic>? ?? {};
    return AssumptionMatrixModel(
      projectId: int.tryParse(json['project_id']?.toString() ?? '') ?? 0,
      totalHypotheses: json['total_hypotheses'] ?? 0,
      criticalCount: json['critical_count'] ?? 0,
      criticalTestFirst: (quads['critical_test_first'] as List<dynamic>?)
              ?.map((item) => HypothesisModel.fromJson(item))
              .toList() ??
          [],
      monitor: (quads['monitor'] as List<dynamic>?)
              ?.map((item) => HypothesisModel.fromJson(item))
              .toList() ??
          [],
      importantLowRisk: (quads['important_low_risk'] as List<dynamic>?)
              ?.map((item) => HypothesisModel.fromJson(item))
              .toList() ??
          [],
      lowPriority: (quads['low_priority'] as List<dynamic>?)
              ?.map((item) => HypothesisModel.fromJson(item))
              .toList() ??
          [],
    );
  }
}
