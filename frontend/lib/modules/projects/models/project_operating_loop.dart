// Task 4 (2026-09-14 remediation) — model này giải mã ĐÚNG hình dạng thật
// của `GET /operations/projects/:projectId/operating-loop` (xem
// `services/company/operations/services/project-operating-loop.service.ts`
// interface `ProjectOperatingLoop`, và `Project` trong `project.service.ts`).
// Bản cũ có `activeCycle.weeklyPlans[]`, `commitments`/`tasks` lồng trong
// cycle/week, `objectives[].keyResults[]` phẳng không wrapper, và field
// `evidence`/`decisions` hoàn toàn không tồn tại ở backend — tất cả đã bị
// xoá. Mọi cấp lồng nhau ở đây là 1 wrapper object ghép entity với mảng con
// của nó, đúng như response thật trả về.

class ProjectSummary {
  final String id;
  final String workspaceId;
  final String title;
  final String? description;
  final String lifecycleStage;
  final int stageVersion;
  final String? stageEnteredAt;
  final String status;
  final String? ownerMemberId;
  final String? projectType;
  final String? strategicPriority;
  final String? portfolioId;
  final String? startDate;
  final String? endDate;
  final String createdAt;

  ProjectSummary({
    required this.id,
    required this.workspaceId,
    required this.title,
    this.description,
    required this.lifecycleStage,
    required this.stageVersion,
    this.stageEnteredAt,
    required this.status,
    this.ownerMemberId,
    this.projectType,
    this.strategicPriority,
    this.portfolioId,
    this.startDate,
    this.endDate,
    required this.createdAt,
  });

  factory ProjectSummary.fromJson(Map<String, dynamic> json) {
    return ProjectSummary(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      lifecycleStage: json['lifecycleStage'] as String? ?? '',
      stageVersion: (json['stageVersion'] as num?)?.toInt() ?? 0,
      stageEnteredAt: json['stageEnteredAt']?.toString(),
      status: json['status'] as String? ?? 'ACTIVE',
      ownerMemberId: json['ownerMemberId']?.toString(),
      projectType: json['projectType'] as String?,
      strategicPriority: json['strategicPriority'] as String?,
      portfolioId: json['portfolioId']?.toString(),
      startDate: json['startDate']?.toString(),
      endDate: json['endDate']?.toString(),
      createdAt: json['createdAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'title': title,
    'description': description,
    'lifecycleStage': lifecycleStage,
    'stageVersion': stageVersion,
    'stageEnteredAt': stageEnteredAt,
    'status': status,
    'ownerMemberId': ownerMemberId,
    'projectType': projectType,
    'strategicPriority': strategicPriority,
    'portfolioId': portfolioId,
    'startDate': startDate,
    'endDate': endDate,
    'createdAt': createdAt,
  };
}

/// `OkrObjectiveDto` — entity Objective, không mang `keyResults` (đó là
/// wrapper `LoopObjectiveTree` bên ngoài).
class LoopObjective {
  final String id;
  final String workspaceId;
  final String projectId;
  final String title;
  final String? why;
  final String? ownerMemberId;
  final String status;
  final String createdAt;
  final String updatedAt;

  LoopObjective({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.title,
    this.why,
    this.ownerMemberId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoopObjective.fromJson(Map<String, dynamic> json) {
    return LoopObjective(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      why: json['why'] as String?,
      ownerMemberId: json['ownerMemberId']?.toString(),
      status: json['status'] as String? ?? 'active',
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'projectId': projectId,
    'title': title,
    'why': why,
    'ownerMemberId': ownerMemberId,
    'status': status,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

/// `KeyResultDto` — entity Key Result, không mang `initiatives` (đó là
/// wrapper `LoopKeyResultTree` bên ngoài).
class LoopKeyResult {
  final String id;
  final String workspaceId;
  final String objectiveId;
  final String? title;
  final String? metricId;
  final double? baselineValue;
  final double? currentValue;
  final double? targetValue;
  final String? unit;
  final String? cadence;
  final String? metricType;
  final String scoringType;
  final String status;
  final String createdAt;
  final String updatedAt;

  LoopKeyResult({
    required this.id,
    required this.workspaceId,
    required this.objectiveId,
    this.title,
    this.metricId,
    this.baselineValue,
    this.currentValue,
    this.targetValue,
    this.unit,
    this.cadence,
    this.metricType,
    required this.scoringType,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoopKeyResult.fromJson(Map<String, dynamic> json) {
    return LoopKeyResult(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      objectiveId: json['objectiveId']?.toString() ?? '',
      title: json['title'] as String?,
      metricId: json['metricId']?.toString(),
      baselineValue: (json['baselineValue'] as num?)?.toDouble(),
      currentValue: (json['currentValue'] as num?)?.toDouble(),
      targetValue: (json['targetValue'] as num?)?.toDouble(),
      unit: json['unit'] as String?,
      cadence: json['cadence'] as String?,
      metricType: json['metricType'] as String?,
      scoringType: json['scoringType'] as String? ?? '',
      status: json['status'] as String? ?? 'active',
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'objectiveId': objectiveId,
    'title': title,
    'metricId': metricId,
    'baselineValue': baselineValue,
    'currentValue': currentValue,
    'targetValue': targetValue,
    'unit': unit,
    'cadence': cadence,
    'metricType': metricType,
    'scoringType': scoringType,
    'status': status,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

/// `InitiativeDto`.
class LoopInitiative {
  final String id;
  final String workspaceId;
  final String projectId;
  final String keyResultId;
  final String title;
  final String status;
  final String? ownerMemberId;
  final String? description;
  final String? intendedOutcome;
  final String? startDate;
  final String? targetDate;
  final String approvalStatus;
  final String createdAt;
  final String updatedAt;

  LoopInitiative({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.keyResultId,
    required this.title,
    required this.status,
    this.ownerMemberId,
    this.description,
    this.intendedOutcome,
    this.startDate,
    this.targetDate,
    required this.approvalStatus,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoopInitiative.fromJson(Map<String, dynamic> json) {
    return LoopInitiative(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      keyResultId: json['keyResultId']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'DRAFT',
      ownerMemberId: json['ownerMemberId']?.toString(),
      description: json['description'] as String?,
      intendedOutcome: json['intendedOutcome'] as String?,
      startDate: json['startDate']?.toString(),
      targetDate: json['targetDate']?.toString(),
      approvalStatus: json['approvalStatus'] as String? ?? '',
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'projectId': projectId,
    'keyResultId': keyResultId,
    'title': title,
    'status': status,
    'ownerMemberId': ownerMemberId,
    'description': description,
    'intendedOutcome': intendedOutcome,
    'startDate': startDate,
    'targetDate': targetDate,
    'approvalStatus': approvalStatus,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

/// Wrapper `{ keyResult, initiatives }` — đúng 1 cấp lồng thật sự ở server.
class LoopKeyResultTree {
  final LoopKeyResult keyResult;
  final List<LoopInitiative> initiatives;

  LoopKeyResultTree({required this.keyResult, this.initiatives = const []});

  factory LoopKeyResultTree.fromJson(Map<String, dynamic> json) {
    return LoopKeyResultTree(
      keyResult: LoopKeyResult.fromJson(
        json['keyResult'] as Map<String, dynamic>? ?? {},
      ),
      initiatives: (json['initiatives'] as List<dynamic>? ?? [])
          .map((e) => LoopInitiative.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'keyResult': keyResult.toJson(),
    'initiatives': initiatives.map((i) => i.toJson()).toList(),
  };
}

/// Wrapper `{ objective, keyResults }` — đúng 1 cấp lồng thật sự ở server.
class LoopObjectiveTree {
  final LoopObjective objective;
  final List<LoopKeyResultTree> keyResults;

  LoopObjectiveTree({required this.objective, this.keyResults = const []});

  factory LoopObjectiveTree.fromJson(Map<String, dynamic> json) {
    return LoopObjectiveTree(
      objective: LoopObjective.fromJson(
        json['objective'] as Map<String, dynamic>? ?? {},
      ),
      keyResults: (json['keyResults'] as List<dynamic>? ?? [])
          .map((e) => LoopKeyResultTree.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'objective': objective.toJson(),
    'keyResults': keyResults.map((kr) => kr.toJson()).toList(),
  };
}

/// `TaskDto`.
class LoopTask {
  final String id;
  final String workspaceId;
  final String projectId;
  final String? weeklyCommitmentId;
  final String? initiativeId;
  final String? weeklyPlanId;
  final String? keyResultId;
  final String title;
  final String status;
  final String priority;
  final String? plannedStartAt;
  final String? dueAt;
  final String timezone;
  final String? assigneeMemberId;
  final String? executionMode;
  final String createdAt;
  final String updatedAt;

  LoopTask({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.weeklyCommitmentId,
    this.initiativeId,
    this.weeklyPlanId,
    this.keyResultId,
    required this.title,
    required this.status,
    required this.priority,
    this.plannedStartAt,
    this.dueAt,
    required this.timezone,
    this.assigneeMemberId,
    this.executionMode,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoopTask.fromJson(Map<String, dynamic> json) {
    return LoopTask(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      weeklyCommitmentId: json['weeklyCommitmentId']?.toString(),
      initiativeId: json['initiativeId']?.toString(),
      weeklyPlanId: json['weeklyPlanId']?.toString(),
      keyResultId: json['keyResultId']?.toString(),
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'todo',
      priority: json['priority'] as String? ?? 'medium',
      plannedStartAt: json['plannedStartAt']?.toString(),
      dueAt: json['dueAt']?.toString(),
      timezone: json['timezone'] as String? ?? 'UTC',
      assigneeMemberId: json['assigneeMemberId']?.toString(),
      executionMode: json['executionMode'] as String?,
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'projectId': projectId,
    'weeklyCommitmentId': weeklyCommitmentId,
    'initiativeId': initiativeId,
    'weeklyPlanId': weeklyPlanId,
    'keyResultId': keyResultId,
    'title': title,
    'status': status,
    'priority': priority,
    'plannedStartAt': plannedStartAt,
    'dueAt': dueAt,
    'timezone': timezone,
    'assigneeMemberId': assigneeMemberId,
    'executionMode': executionMode,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

/// `WeeklyCommitmentDto` — root-level array, KHÔNG lồng trong cycle/week.
class LoopCommitment {
  final String id;
  final String workspaceId;
  final String projectId;
  final String weeklyPlanId;
  final String? initiativeId;
  final String title;
  final String status;
  final String? plannedEffort;
  final String purposeType;
  final String? purposeRef;
  final String? ownerMemberId;
  final String? executionMode;
  final String? committedAt;
  final String createdAt;
  final String updatedAt;

  LoopCommitment({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.weeklyPlanId,
    this.initiativeId,
    required this.title,
    required this.status,
    this.plannedEffort,
    required this.purposeType,
    this.purposeRef,
    this.ownerMemberId,
    this.executionMode,
    this.committedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoopCommitment.fromJson(Map<String, dynamic> json) {
    return LoopCommitment(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      weeklyPlanId: json['weeklyPlanId']?.toString() ?? '',
      initiativeId: json['initiativeId']?.toString(),
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'committed',
      plannedEffort: json['plannedEffort']?.toString(),
      purposeType: json['purposeType'] as String? ?? '',
      purposeRef: json['purposeRef']?.toString(),
      ownerMemberId: json['ownerMemberId']?.toString(),
      executionMode: json['executionMode'] as String?,
      committedAt: json['committedAt']?.toString(),
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'projectId': projectId,
    'weeklyPlanId': weeklyPlanId,
    'initiativeId': initiativeId,
    'title': title,
    'status': status,
    'plannedEffort': plannedEffort,
    'purposeType': purposeType,
    'purposeRef': purposeRef,
    'ownerMemberId': ownerMemberId,
    'executionMode': executionMode,
    'committedAt': committedAt,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

/// `WeeklyPlanDto` — root-level `currentWeek`, KHÔNG mang `commitments`.
class LoopWeek {
  final String id;
  final String workspaceId;
  final String projectId;
  final String cycleId;
  final int weekNo;
  final String? focus;
  final String? mission;
  final double? executionScore;
  final double? outcomeScore;
  final String? reflection;
  final String? startDate;
  final String? endDate;
  final String createdAt;
  final String updatedAt;

  LoopWeek({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.cycleId,
    required this.weekNo,
    this.focus,
    this.mission,
    this.executionScore,
    this.outcomeScore,
    this.reflection,
    this.startDate,
    this.endDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LoopWeek.fromJson(Map<String, dynamic> json) {
    return LoopWeek(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      cycleId: json['cycleId']?.toString() ?? '',
      weekNo: (json['weekNo'] as num?)?.toInt() ?? 1,
      focus: json['focus'] as String?,
      mission: json['mission'] as String?,
      executionScore: (json['executionScore'] as num?)?.toDouble(),
      outcomeScore: (json['outcomeScore'] as num?)?.toDouble(),
      reflection: json['reflection'] as String?,
      startDate: json['startDate']?.toString(),
      endDate: json['endDate']?.toString(),
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'projectId': projectId,
    'cycleId': cycleId,
    'weekNo': weekNo,
    'focus': focus,
    'mission': mission,
    'executionScore': executionScore,
    'outcomeScore': outcomeScore,
    'reflection': reflection,
    'startDate': startDate,
    'endDate': endDate,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
  };
}

/// `CycleDto`.
class LoopActiveCycle {
  final String id;
  final String workspaceId;
  final String projectId;
  final int currentWeek;
  final int durationWeeks;
  final String? theme;
  final String visionStatement;
  final String status;
  final String timezone;
  final String? startLocalDate;
  final String? startDate;
  final String? endDate;
  final String createdAt;
  final String updatedAt;
  final String? sourceObjectiveId;

  LoopActiveCycle({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.currentWeek,
    required this.durationWeeks,
    this.theme,
    required this.visionStatement,
    required this.status,
    required this.timezone,
    this.startLocalDate,
    this.startDate,
    this.endDate,
    required this.createdAt,
    required this.updatedAt,
    this.sourceObjectiveId,
  });

  factory LoopActiveCycle.fromJson(Map<String, dynamic> json) {
    return LoopActiveCycle(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      currentWeek: (json['currentWeek'] as num?)?.toInt() ?? 1,
      durationWeeks: (json['durationWeeks'] as num?)?.toInt() ?? 12,
      theme: json['theme'] as String?,
      visionStatement: json['visionStatement'] as String? ?? '',
      status: json['status'] as String? ?? 'active',
      timezone: json['timezone'] as String? ?? 'UTC',
      startLocalDate: json['startLocalDate']?.toString(),
      startDate: json['startDate']?.toString(),
      endDate: json['endDate']?.toString(),
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
      sourceObjectiveId: json['sourceObjectiveId']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'projectId': projectId,
    'currentWeek': currentWeek,
    'durationWeeks': durationWeeks,
    'theme': theme,
    'visionStatement': visionStatement,
    'status': status,
    'timezone': timezone,
    'startLocalDate': startLocalDate,
    'startDate': startDate,
    'endDate': endDate,
    'createdAt': createdAt,
    'updatedAt': updatedAt,
    'sourceObjectiveId': sourceObjectiveId,
  };
}

/// Root DTO — khớp chính xác `ProjectOperatingLoop` (TS) tại
/// `project-operating-loop.service.ts`. `activeCycle` và `currentWeek` là 2
/// field SIBLING ở gốc; `commitments`/`tasks` cũng là mảng gốc, không lồng
/// trong cycle/week. KHÔNG có `evidence`/`decisions` — backend không có bảng
/// hay endpoint nào hậu thuẫn 2 khái niệm đó trong DTO này.
class ProjectOperatingLoop {
  final ProjectSummary project;
  final LoopActiveCycle? activeCycle;
  final LoopWeek? currentWeek;
  final List<LoopCommitment> commitments;
  final List<LoopObjectiveTree> objectives;
  final List<LoopTask> tasks;

  ProjectOperatingLoop({
    required this.project,
    this.activeCycle,
    this.currentWeek,
    this.commitments = const [],
    this.objectives = const [],
    this.tasks = const [],
  });

  factory ProjectOperatingLoop.fromJson(Map<String, dynamic> json) {
    return ProjectOperatingLoop(
      project: ProjectSummary.fromJson(
        json['project'] as Map<String, dynamic>? ?? {},
      ),
      activeCycle: json['activeCycle'] != null
          ? LoopActiveCycle.fromJson(json['activeCycle'] as Map<String, dynamic>)
          : null,
      currentWeek: json['currentWeek'] != null
          ? LoopWeek.fromJson(json['currentWeek'] as Map<String, dynamic>)
          : null,
      commitments: (json['commitments'] as List<dynamic>? ?? [])
          .map((e) => LoopCommitment.fromJson(e as Map<String, dynamic>))
          .toList(),
      objectives: (json['objectives'] as List<dynamic>? ?? [])
          .map((e) => LoopObjectiveTree.fromJson(e as Map<String, dynamic>))
          .toList(),
      tasks: (json['tasks'] as List<dynamic>? ?? [])
          .map((e) => LoopTask.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'project': project.toJson(),
    'activeCycle': activeCycle?.toJson(),
    'currentWeek': currentWeek?.toJson(),
    'commitments': commitments.map((c) => c.toJson()).toList(),
    'objectives': objectives.map((o) => o.toJson()).toList(),
    'tasks': tasks.map((t) => t.toJson()).toList(),
  };
}
