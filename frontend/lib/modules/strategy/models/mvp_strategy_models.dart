import '../../../core/network/api_result.dart';

class MvpCanvas {
  final String id;
  final String workspaceId;
  final String name;
  final String? description;
  final String? currentRevisionId;
  final String? createdByMemberId;
  final String createdAt;
  final String updatedAt;

  const MvpCanvas({
    required this.id,
    required this.workspaceId,
    required this.name,
    this.description,
    this.currentRevisionId,
    this.createdByMemberId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MvpCanvas.fromJson(Map<String, dynamic> json) {
    return MvpCanvas(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      currentRevisionId: json['currentRevisionId']?.toString(),
      createdByMemberId: json['createdByMemberId']?.toString(),
      createdAt: json['createdAt'] as String? ?? '',
      updatedAt: json['updatedAt'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'workspaceId': workspaceId,
        'name': name,
        'description': description,
        'currentRevisionId': currentRevisionId,
        'createdByMemberId': createdByMemberId,
        'createdAt': createdAt,
        'updatedAt': updatedAt,
      };
}

class MvpCanvasRevision {
  final String id;
  final String workspaceId;
  final String canvasId;
  final String? parentRevisionId;
  final Map<String, dynamic> content;
  final String status;
  final String origin;
  final List<ApiSourceRef> sourceRefs;
  final String? createdByMemberId;
  final String? reviewedByMemberId;
  final String? reviewNote;
  final String createdAt;
  final String? reviewedAt;

  const MvpCanvasRevision({
    required this.id,
    required this.workspaceId,
    required this.canvasId,
    this.parentRevisionId,
    required this.content,
    required this.status,
    required this.origin,
    required this.sourceRefs,
    this.createdByMemberId,
    this.reviewedByMemberId,
    this.reviewNote,
    required this.createdAt,
    this.reviewedAt,
  });

  factory MvpCanvasRevision.fromJson(Map<String, dynamic> json) {
    final rawRefs = json['sourceRefs'] as List<dynamic>? ?? [];
    final refs = rawRefs
        .whereType<Map<String, dynamic>>()
        .map((r) => ApiSourceRef(
              kind: r['kind'] as String? ?? 'unknown',
              ref: r['ref'] as String? ?? '',
              observedAt: r['observed_at'] != null || r['observedAt'] != null
                  ? DateTime.tryParse((r['observed_at'] ?? r['observedAt']).toString())
                  : null,
            ))
        .toList();

    return MvpCanvasRevision(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      canvasId: json['canvasId']?.toString() ?? '',
      parentRevisionId: json['parentRevisionId']?.toString(),
      content: json['content'] as Map<String, dynamic>? ?? {},
      status: json['status'] as String? ?? 'DRAFT',
      origin: json['origin'] as String? ?? 'USER',
      sourceRefs: refs,
      createdByMemberId: json['createdByMemberId']?.toString(),
      reviewedByMemberId: json['reviewedByMemberId']?.toString(),
      reviewNote: json['reviewNote'] as String?,
      createdAt: json['createdAt'] as String? ?? '',
      reviewedAt: json['reviewedAt'] as String?,
    );
  }
}

class MvpOkrCycle {
  final String id;
  final String workspaceId;
  final String name;
  final String status;
  final String createdAt;

  const MvpOkrCycle({
    required this.id,
    required this.workspaceId,
    required this.name,
    required this.status,
    required this.createdAt,
  });

  factory MvpOkrCycle.fromJson(Map<String, dynamic> json) {
    return MvpOkrCycle(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      status: json['status'] as String? ?? '',
      createdAt: json['createdAt'] as String? ?? '',
    );
  }
}

class MvpObjective {
  final String id;
  final String workspaceId;
  final String cycleId;
  final String title;
  final String? why;
  final String? ownerMemberId;
  final String status;
  final List<String> projectIds;
  final String createdAt;

  const MvpObjective({
    required this.id,
    required this.workspaceId,
    required this.cycleId,
    required this.title,
    this.why,
    this.ownerMemberId,
    required this.status,
    required this.projectIds,
    required this.createdAt,
  });

  factory MvpObjective.fromJson(Map<String, dynamic> json) {
    final rawProjects = json['projectIds'] as List<dynamic>? ?? [];
    return MvpObjective(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      cycleId: json['cycleId']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      why: json['why'] as String?,
      ownerMemberId: json['ownerMemberId']?.toString(),
      status: json['status'] as String? ?? 'DRAFT',
      projectIds: rawProjects.map((p) => p.toString()).toList(),
      createdAt: json['createdAt'] as String? ?? '',
    );
  }
}

class MvpObjectiveProgress {
  final String objectiveId;
  final double score;
  final List<MvpKeyResultProgress> keyResults;

  const MvpObjectiveProgress({
    required this.objectiveId,
    required this.score,
    required this.keyResults,
  });

  factory MvpObjectiveProgress.fromJson(Map<String, dynamic> json) {
    final rawKrs = json['keyResults'] as List<dynamic>? ?? [];
    return MvpObjectiveProgress(
      objectiveId: json['objectiveId']?.toString() ?? '',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      keyResults: rawKrs
          .whereType<Map<String, dynamic>>()
          .map((k) => MvpKeyResultProgress.fromJson(k))
          .toList(),
    );
  }
}

class MvpKeyResultProgress {
  final String id;
  final String? title;
  final double score;

  const MvpKeyResultProgress({
    required this.id,
    this.title,
    required this.score,
  });

  factory MvpKeyResultProgress.fromJson(Map<String, dynamic> json) {
    return MvpKeyResultProgress(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String?,
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class MvpTwelveWeekCycle {
  final String id;
  final String workspaceId;
  final String? projectId;
  final String? theme;
  final String visionStatement;
  final String stageAtStart;
  final int currentWeek;
  final int durationWeeks;
  final double overallExecutionScore;
  final String? startDate;
  final String? endDate;
  final String? commitmentLevel;
  final String status;
  final String createdAt;

  const MvpTwelveWeekCycle({
    required this.id,
    required this.workspaceId,
    this.projectId,
    this.theme,
    required this.visionStatement,
    required this.stageAtStart,
    required this.currentWeek,
    required this.durationWeeks,
    required this.overallExecutionScore,
    this.startDate,
    this.endDate,
    this.commitmentLevel,
    required this.status,
    required this.createdAt,
  });

  factory MvpTwelveWeekCycle.fromJson(Map<String, dynamic> json) {
    return MvpTwelveWeekCycle(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString(),
      theme: json['theme'] as String?,
      visionStatement: json['visionStatement'] as String? ?? '',
      stageAtStart: json['stageAtStart'] as String? ?? '',
      currentWeek: (json['currentWeek'] as num?)?.toInt() ?? 1,
      durationWeeks: (json['durationWeeks'] as num?)?.toInt() ?? 12,
      overallExecutionScore: (json['overallExecutionScore'] as num?)?.toDouble() ?? 0.0,
      startDate: json['startDate'] as String?,
      endDate: json['endDate'] as String?,
      commitmentLevel: json['commitmentLevel'] as String?,
      status: json['status'] as String? ?? 'ACTIVE',
      createdAt: json['createdAt'] as String? ?? '',
    );
  }
}

class MvpWeeklyPlan {
  final String id;
  final String workspaceId;
  final String cycleId;
  final int weekNo;
  final String? startDate;
  final String? endDate;
  final String? focus;
  final String? mission;
  final double? executionScore;
  final double? outcomeScore;
  final String? reflection;
  final String createdAt;

  const MvpWeeklyPlan({
    required this.id,
    required this.workspaceId,
    required this.cycleId,
    required this.weekNo,
    this.startDate,
    this.endDate,
    this.focus,
    this.mission,
    this.executionScore,
    this.outcomeScore,
    this.reflection,
    required this.createdAt,
  });

  factory MvpWeeklyPlan.fromJson(Map<String, dynamic> json) {
    return MvpWeeklyPlan(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      cycleId: json['cycleId']?.toString() ?? '',
      weekNo: (json['weekNo'] as num?)?.toInt() ?? 1,
      startDate: json['startDate'] as String?,
      endDate: json['endDate'] as String?,
      focus: json['focus'] as String?,
      mission: json['mission'] as String?,
      executionScore: (json['executionScore'] as num?)?.toDouble(),
      outcomeScore: (json['outcomeScore'] as num?)?.toDouble(),
      reflection: json['reflection'] as String?,
      createdAt: json['createdAt'] as String? ?? '',
    );
  }
}

class MvpWeeklyCommitment {
  final String id;
  final String workspaceId;
  final String weeklyPlanId;
  final String? initiativeId;
  final String title;
  final String status;
  final String? plannedEffort;
  final String? commitmentOwnerType;
  final String? executionMode;
  final String createdAt;

  const MvpWeeklyCommitment({
    required this.id,
    required this.workspaceId,
    required this.weeklyPlanId,
    this.initiativeId,
    required this.title,
    required this.status,
    this.plannedEffort,
    this.commitmentOwnerType,
    this.executionMode,
    required this.createdAt,
  });

  factory MvpWeeklyCommitment.fromJson(Map<String, dynamic> json) {
    return MvpWeeklyCommitment(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      weeklyPlanId: json['weeklyPlanId']?.toString() ?? '',
      initiativeId: json['initiativeId']?.toString(),
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'PENDING',
      plannedEffort: json['plannedEffort'] as String?,
      commitmentOwnerType: json['commitmentOwnerType'] as String?,
      executionMode: json['executionMode'] as String?,
      createdAt: json['createdAt'] as String? ?? '',
    );
  }
}
