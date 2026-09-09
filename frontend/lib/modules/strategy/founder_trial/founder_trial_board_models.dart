/// Client model cho Founder Trial Board (spec §4). Read-only, ghép từ dữ liệu
/// thật: Operating Cycle → Assumptions → Experiments → Evidence → Decision.
library;

class FounderTrialCycle {
  const FounderTrialCycle({
    required this.cycleId,
    required this.durationWeeks,
    required this.currentWeek,
    required this.stageAtStart,
    required this.calendarState,
    required this.startLocalDate,
    required this.timezone,
    required this.reviews,
  });

  final String? cycleId;
  final int? durationWeeks;
  final int? currentWeek;
  final String? stageAtStart;
  final String? calendarState;
  final String? startLocalDate;
  final String? timezone;
  final List<FounderTrialReviewSlot> reviews;

  factory FounderTrialCycle.fromJson(Map<String, dynamic> json) {
    return FounderTrialCycle(
      cycleId: json['cycleId']?.toString(),
      durationWeeks: (json['durationWeeks'] as num?)?.toInt(),
      currentWeek: (json['currentWeek'] as num?)?.toInt(),
      stageAtStart: json['stageAtStart']?.toString(),
      calendarState: json['calendarState']?.toString(),
      startLocalDate: json['startLocalDate']?.toString(),
      timezone: json['timezone']?.toString(),
      reviews: (json['reviews'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(FounderTrialReviewSlot.fromJson)
              .toList() ??
          const [],
    );
  }
}

class FounderTrialReviewSlot {
  const FounderTrialReviewSlot({
    required this.id,
    required this.kind,
    required this.scheduledWeekNo,
    required this.scheduledAt,
    required this.status,
  });

  final String id;
  final String kind;
  final int scheduledWeekNo;
  final String? scheduledAt;
  final String status;

  factory FounderTrialReviewSlot.fromJson(Map<String, dynamic> json) {
    return FounderTrialReviewSlot(
      id: json['id']?.toString() ?? '',
      kind: json['kind']?.toString() ?? '',
      scheduledWeekNo: (json['scheduledWeekNo'] as num?)?.toInt() ?? 0,
      scheduledAt: json['scheduledAt']?.toString(),
      status: json['status']?.toString() ?? '',
    );
  }
}

class FounderTrialAssumption {
  const FounderTrialAssumption({
    required this.id,
    required this.statement,
    required this.importance,
    required this.uncertainty,
    required this.riskScore,
    required this.status,
    required this.rank,
    required this.isFocus,
  });

  final String id;
  final String statement;
  final int importance;
  final int uncertainty;
  final int riskScore;
  final String status;
  final int rank;
  final bool isFocus;

  factory FounderTrialAssumption.fromJson(Map<String, dynamic> json) {
    return FounderTrialAssumption(
      id: json['id']?.toString() ?? '',
      statement: json['statement']?.toString() ?? '',
      importance: (json['importance'] as num?)?.toInt() ?? 0,
      uncertainty: (json['uncertainty'] as num?)?.toInt() ?? 0,
      riskScore: (json['riskScore'] as num?)?.toInt() ?? 0,
      status: json['status']?.toString() ?? 'untested',
      rank: (json['rank'] as num?)?.toInt() ?? 0,
      isFocus: json['isFocus'] == true,
    );
  }
}

class FounderTrialExperiment {
  const FounderTrialExperiment({
    required this.id,
    required this.assumptionId,
    required this.hypothesis,
    required this.method,
    required this.successCriteria,
    required this.status,
    required this.linkedToAssumption,
  });

  final String id;
  final String? assumptionId;
  final String hypothesis;
  final String method;
  final String successCriteria;
  final String status;
  final bool linkedToAssumption;

  factory FounderTrialExperiment.fromJson(Map<String, dynamic> json) {
    return FounderTrialExperiment(
      id: json['id']?.toString() ?? '',
      assumptionId: json['assumptionId']?.toString(),
      hypothesis: json['hypothesis']?.toString() ?? '',
      method: json['method']?.toString() ?? '',
      successCriteria: json['successCriteria']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      linkedToAssumption: json['linkedToAssumption'] == true,
    );
  }
}

class FounderTrialEvidence {
  const FounderTrialEvidence({
    required this.id,
    required this.claim,
    required this.status,
    required this.supportsOrRefutes,
    required this.sourceType,
    required this.experimentId,
    required this.linkedToExperiment,
    required this.observedAt,
  });

  final String id;
  final String claim;
  final String status;
  final String supportsOrRefutes;
  final String sourceType;
  final String? experimentId;
  final bool linkedToExperiment;
  final String? observedAt;

  factory FounderTrialEvidence.fromJson(Map<String, dynamic> json) {
    return FounderTrialEvidence(
      id: json['id']?.toString() ?? '',
      claim: json['claim']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      supportsOrRefutes: json['supportsOrRefutes']?.toString() ?? '',
      sourceType: json['sourceType']?.toString() ?? '',
      experimentId: json['experimentId']?.toString(),
      linkedToExperiment: json['linkedToExperiment'] == true,
      observedAt: json['observedAt']?.toString(),
    );
  }
}

class FounderTrialDecision {
  const FounderTrialDecision({
    required this.id,
    required this.decision,
    required this.createdAt,
  });

  final String id;
  final String decision;
  final String createdAt;

  factory FounderTrialDecision.fromJson(Map<String, dynamic> json) {
    return FounderTrialDecision(
      id: json['id']?.toString() ?? '',
      decision: json['decision']?.toString() ?? '',
      createdAt: json['createdAt']?.toString() ?? '',
    );
  }
}

class FounderTrialBoard {
  const FounderTrialBoard({
    required this.projectId,
    required this.cycle,
    required this.assumptions,
    required this.experiments,
    required this.evidenceCandidate,
    required this.evidenceApproved,
    required this.evidenceRejected,
    required this.evidenceUnlinked,
    required this.decisions,
  });

  final String projectId;
  final FounderTrialCycle cycle;
  final List<FounderTrialAssumption> assumptions;
  final List<FounderTrialExperiment> experiments;
  final List<FounderTrialEvidence> evidenceCandidate;
  final List<FounderTrialEvidence> evidenceApproved;
  final List<FounderTrialEvidence> evidenceRejected;
  final List<FounderTrialEvidence> evidenceUnlinked;
  final List<FounderTrialDecision> decisions;

  List<FounderTrialAssumption> get focusAssumptions =>
      assumptions.where((a) => a.isFocus).toList();

  factory FounderTrialBoard.fromJson(Map<String, dynamic> json) {
    List<FounderTrialEvidence> ev(dynamic v) => (v as List?)
            ?.whereType<Map<String, dynamic>>()
            .map(FounderTrialEvidence.fromJson)
            .toList() ??
        const [];
    final evidence = (json['evidence'] as Map<String, dynamic>?) ?? const {};
    return FounderTrialBoard(
      projectId: json['projectId']?.toString() ?? '',
      cycle: FounderTrialCycle.fromJson(
          (json['cycle'] as Map<String, dynamic>?) ?? const {}),
      assumptions: (json['assumptions'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(FounderTrialAssumption.fromJson)
              .toList() ??
          const [],
      experiments: (json['experiments'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(FounderTrialExperiment.fromJson)
              .toList() ??
          const [],
      evidenceCandidate: ev(evidence['candidate']),
      evidenceApproved: ev(evidence['approved']),
      evidenceRejected: ev(evidence['rejected']),
      evidenceUnlinked: ev(evidence['unlinked']),
      decisions: (json['decisions'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(FounderTrialDecision.fromJson)
              .toList() ??
          const [],
    );
  }
}
