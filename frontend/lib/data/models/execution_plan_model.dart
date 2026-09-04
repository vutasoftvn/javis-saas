/// WGA — Execution Plan (kế hoạch triển khai agent đề xuất từ mục tiêu tuần).
library;

enum AutonomyClass { auto, needsApproval, founderOnly }

AutonomyClass autonomyClassFromString(String? raw) {
  switch (raw) {
    case 'AUTO':
      return AutonomyClass.auto;
    case 'FOUNDER_ONLY':
      return AutonomyClass.founderOnly;
    case 'NEEDS_APPROVAL':
    default:
      return AutonomyClass.needsApproval;
  }
}

String autonomyClassToString(AutonomyClass c) {
  switch (c) {
    case AutonomyClass.auto:
      return 'AUTO';
    case AutonomyClass.founderOnly:
      return 'FOUNDER_ONLY';
    case AutonomyClass.needsApproval:
      return 'NEEDS_APPROVAL';
  }
}

String autonomyClassLabel(AutonomyClass c) {
  switch (c) {
    case AutonomyClass.auto:
      return 'AI tự làm';
    case AutonomyClass.needsApproval:
      return 'Cần bạn duyệt';
    case AutonomyClass.founderOnly:
      return 'Bạn tự làm';
  }
}

class ExecutionPlanItem {
  final String id;
  final String title;
  final String decisionReason;
  final List<String> evidenceRefs;
  final String? ownerAgentProfile;
  final String? expectedCapability;
  final AutonomyClass autonomyClass;
  final String autonomyClassSource;
  final String priority;
  final List<String> dependsOnItemIds;
  final String status; // proposed | accepted | dropped
  final String? materializedTaskId;

  const ExecutionPlanItem({
    required this.id,
    required this.title,
    required this.decisionReason,
    required this.evidenceRefs,
    required this.ownerAgentProfile,
    required this.expectedCapability,
    required this.autonomyClass,
    required this.autonomyClassSource,
    required this.priority,
    required this.dependsOnItemIds,
    required this.status,
    required this.materializedTaskId,
  });

  bool get needsEvidence =>
      autonomyClass != AutonomyClass.founderOnly && evidenceRefs.isEmpty;

  factory ExecutionPlanItem.fromJson(Map<String, dynamic> j) {
    return ExecutionPlanItem(
      id: '${j['id']}',
      title: (j['title'] ?? '') as String,
      decisionReason: (j['decisionReason'] ?? '') as String,
      evidenceRefs:
          ((j['evidenceRefs'] as List<dynamic>?) ?? const []).map((e) => '$e').toList(),
      ownerAgentProfile: j['ownerAgentProfile'] as String?,
      expectedCapability: j['expectedCapability'] as String?,
      autonomyClass: autonomyClassFromString(j['autonomyClass'] as String?),
      autonomyClassSource: (j['autonomyClassSource'] ?? 'classifier_default') as String,
      priority: (j['priority'] ?? 'medium') as String,
      dependsOnItemIds:
          ((j['dependsOnItemIds'] as List<dynamic>?) ?? const []).map((e) => '$e').toList(),
      status: (j['status'] ?? 'proposed') as String,
      materializedTaskId: j['materializedTaskId'] as String?,
    );
  }
}

/// WGA #6a — "Việc của bạn": task founder tự làm hoặc AI bị chặn.
class FounderInboxTask {
  final String taskId;
  final String title;
  final String status;
  final String priority;
  final String reason; // 'founder_only' | 'blocked'

  const FounderInboxTask({
    required this.taskId,
    required this.title,
    required this.status,
    required this.priority,
    required this.reason,
  });

  bool get isBlocked => reason == 'blocked';

  factory FounderInboxTask.fromJson(Map<String, dynamic> j) => FounderInboxTask(
        taskId: '${j['taskId']}',
        title: (j['title'] ?? '') as String,
        status: (j['status'] ?? '') as String,
        priority: (j['priority'] ?? 'medium') as String,
        reason: (j['reason'] ?? 'founder_only') as String,
      );
}

class ExecutionPlan {
  final String id;
  final String projectId;
  final String? weeklyPlanId;
  final String goalText;
  final String status; // draft | accepted | superseded | rejected
  final String origin;
  final List<ExecutionPlanItem> items;

  const ExecutionPlan({
    required this.id,
    required this.projectId,
    required this.weeklyPlanId,
    required this.goalText,
    required this.status,
    required this.origin,
    required this.items,
  });

  List<ExecutionPlanItem> get liveItems =>
      items.where((i) => i.status != 'dropped').toList();

  bool get canAccept =>
      status == 'draft' && liveItems.isNotEmpty && !liveItems.any((i) => i.needsEvidence);

  factory ExecutionPlan.fromJson(Map<String, dynamic> j) {
    return ExecutionPlan(
      id: '${j['id']}',
      projectId: '${j['projectId']}',
      weeklyPlanId: j['weeklyPlanId'] as String?,
      goalText: (j['goalText'] ?? '') as String,
      status: (j['status'] ?? 'draft') as String,
      origin: (j['origin'] ?? 'command_center') as String,
      items: ((j['items'] as List<dynamic>?) ?? const [])
          .map((e) => ExecutionPlanItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
