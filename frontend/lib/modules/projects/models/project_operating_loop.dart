class ProjectSummary {
  final String id;
  final String workspaceId;
  final String title;
  final String? description;
  final String status;
  final String createdAt;
  final String updatedAt;

  ProjectSummary({
    required this.id,
    required this.workspaceId,
    required this.title,
    this.description,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ProjectSummary.fromJson(Map<String, dynamic> json) {
    return ProjectSummary(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      status: json['status'] as String? ?? 'ACTIVE',
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'title': title,
    'description': description,
    'status': status,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

class LoopInitiative {
  final String id;
  final String title;
  final String status;

  LoopInitiative({
    required this.id,
    required this.title,
    required this.status,
  });

  factory LoopInitiative.fromJson(Map<String, dynamic> json) {
    return LoopInitiative(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'DRAFT',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'status': status,
  };
}

class LoopKeyResult {
  final String id;
  final String title;
  final double? targetValue;
  final double? currentValue;
  final String? metricUnit;
  final List<LoopInitiative> initiatives;

  LoopKeyResult({
    required this.id,
    required this.title,
    this.targetValue,
    this.currentValue,
    this.metricUnit,
    this.initiatives = const [],
  });

  factory LoopKeyResult.fromJson(Map<String, dynamic> json) {
    return LoopKeyResult(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      targetValue: json['targetValue'] != null ? (json['targetValue'] as num).toDouble() : null,
      currentValue: json['currentValue'] != null ? (json['currentValue'] as num).toDouble() : null,
      metricUnit: json['metricUnit'] as String?,
      initiatives: (json['initiatives'] as List<dynamic>? ?? [])
          .map((e) => LoopInitiative.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'targetValue': targetValue,
    'currentValue': currentValue,
    'metricUnit': metricUnit,
    'initiatives': initiatives.map((i) => i.toJson()).toList(),
  };
}

class LoopObjective {
  final String id;
  final String title;
  final String status;
  final List<LoopKeyResult> keyResults;

  LoopObjective({
    required this.id,
    required this.title,
    required this.status,
    this.keyResults = const [],
  });

  factory LoopObjective.fromJson(Map<String, dynamic> json) {
    return LoopObjective(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'active',
      keyResults: (json['keyResults'] as List<dynamic>? ?? [])
          .map((e) => LoopKeyResult.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'status': status,
    'keyResults': keyResults.map((kr) => kr.toJson()).toList(),
  };
}

class LoopTask {
  final String id;
  final String title;
  final String status;
  final String priority;
  final String? assigneeMemberId;
  final String? weeklyCommitmentId;

  LoopTask({
    required this.id,
    required this.title,
    required this.status,
    required this.priority,
    this.assigneeMemberId,
    this.weeklyCommitmentId,
  });

  factory LoopTask.fromJson(Map<String, dynamic> json) {
    return LoopTask(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'todo',
      priority: json['priority'] as String? ?? 'medium',
      assigneeMemberId: json['assigneeMemberId']?.toString(),
      weeklyCommitmentId: json['weeklyCommitmentId']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'status': status,
    'priority': priority,
    'assigneeMemberId': assigneeMemberId,
    'weeklyCommitmentId': weeklyCommitmentId,
  };
}

class LoopCommitment {
  final String id;
  final String title;
  final String status;
  final double? targetConfidence;
  final List<LoopTask> tasks;

  LoopCommitment({
    required this.id,
    required this.title,
    required this.status,
    this.targetConfidence,
    this.tasks = const [],
  });

  factory LoopCommitment.fromJson(Map<String, dynamic> json) {
    return LoopCommitment(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'committed',
      targetConfidence: json['targetConfidence'] != null
          ? (json['targetConfidence'] as num).toDouble()
          : null,
      tasks: (json['tasks'] as List<dynamic>? ?? [])
          .map((e) => LoopTask.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'status': status,
    'targetConfidence': targetConfidence,
    'tasks': tasks.map((t) => t.toJson()).toList(),
  };
}

class LoopWeeklyPlan {
  final String id;
  final int weekNo;
  final String? focus;
  final List<LoopCommitment> commitments;

  LoopWeeklyPlan({
    required this.id,
    required this.weekNo,
    this.focus,
    this.commitments = const [],
  });

  factory LoopWeeklyPlan.fromJson(Map<String, dynamic> json) {
    return LoopWeeklyPlan(
      id: json['id']?.toString() ?? '',
      weekNo: (json['weekNo'] as num?)?.toInt() ?? 1,
      focus: json['focus'] as String?,
      commitments: (json['commitments'] as List<dynamic>? ?? [])
          .map((e) => LoopCommitment.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'weekNo': weekNo,
    'focus': focus,
    'commitments': commitments.map((c) => c.toJson()).toList(),
  };
}

class LoopActiveCycle {
  final String id;
  final int durationWeeks;
  final String startDate;
  final String endDate;
  final int revision;
  final List<LoopWeeklyPlan> weeklyPlans;

  LoopActiveCycle({
    required this.id,
    required this.durationWeeks,
    required this.startDate,
    required this.endDate,
    required this.revision,
    this.weeklyPlans = const [],
  });

  factory LoopActiveCycle.fromJson(Map<String, dynamic> json) {
    return LoopActiveCycle(
      id: json['id']?.toString() ?? '',
      durationWeeks: (json['durationWeeks'] as num?)?.toInt() ?? 12,
      startDate: json['startDate']?.toString() ?? '',
      endDate: json['endDate']?.toString() ?? '',
      revision: (json['revision'] as num?)?.toInt() ?? 1,
      weeklyPlans: (json['weeklyPlans'] as List<dynamic>? ?? [])
          .map((e) => LoopWeeklyPlan.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'durationWeeks': durationWeeks,
    'startDate': startDate,
    'endDate': endDate,
    'revision': revision,
    'weeklyPlans': weeklyPlans.map((w) => w.toJson()).toList(),
  };
}

class LoopEvidence {
  final String id;
  final String title;
  final String status;
  final String sourceType;

  LoopEvidence({
    required this.id,
    required this.title,
    required this.status,
    required this.sourceType,
  });

  factory LoopEvidence.fromJson(Map<String, dynamic> json) {
    return LoopEvidence(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'candidate',
      sourceType: json['sourceType'] as String? ?? 'manual',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'status': status,
    'sourceType': sourceType,
  };
}

class LoopDecision {
  final String id;
  final String title;
  final String status;

  LoopDecision({
    required this.id,
    required this.title,
    required this.status,
  });

  factory LoopDecision.fromJson(Map<String, dynamic> json) {
    return LoopDecision(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'approved',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'status': status,
  };
}

class ProjectOperatingLoop {
  final ProjectSummary project;
  final List<LoopObjective> objectives;
  final LoopActiveCycle? activeCycle;
  final List<LoopTask> tasks;
  final List<LoopEvidence> evidence;
  final List<LoopDecision> decisions;

  ProjectOperatingLoop({
    required this.project,
    this.objectives = const [],
    this.activeCycle,
    this.tasks = const [],
    this.evidence = const [],
    this.decisions = const [],
  });

  factory ProjectOperatingLoop.fromJson(Map<String, dynamic> json) {
    return ProjectOperatingLoop(
      project: ProjectSummary.fromJson(json['project'] as Map<String, dynamic>? ?? {}),
      objectives: (json['objectives'] as List<dynamic>? ?? [])
          .map((e) => LoopObjective.fromJson(e as Map<String, dynamic>))
          .toList(),
      activeCycle: json['activeCycle'] != null
          ? LoopActiveCycle.fromJson(json['activeCycle'] as Map<String, dynamic>)
          : null,
      tasks: (json['tasks'] as List<dynamic>? ?? [])
          .map((e) => LoopTask.fromJson(e as Map<String, dynamic>))
          .toList(),
      evidence: (json['evidence'] as List<dynamic>? ?? [])
          .map((e) => LoopEvidence.fromJson(e as Map<String, dynamic>))
          .toList(),
      decisions: (json['decisions'] as List<dynamic>? ?? [])
          .map((e) => LoopDecision.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'project': project.toJson(),
    'objectives': objectives.map((o) => o.toJson()).toList(),
    'activeCycle': activeCycle?.toJson(),
    'tasks': tasks.map((t) => t.toJson()).toList(),
    'evidence': evidence.map((e) => e.toJson()).toList(),
    'decisions': decisions.map((d) => d.toJson()).toList(),
  };
}
