import 'package:flutter/foundation.dart';

// Task 3 — models chỉ decode đúng field mà backend contract
// (apps/cosa/api/workforce_schemas.py + workforce_routes.py) thực sự trả về.
// Không suy diễn thêm field không tồn tại trên response thật.
//
// Fix-review (2026-09-01) — brief liệt kê `sealed class WorkforceResult<T>`
// trong interface nhưng không subtype/consumer nào cần tới nó: mọi method
// của WorkforceMvpService đã trả `ApiResult<T>` (core/network/api_result.dart),
// vốn đã đảm nhiệm việc phân biệt success/failure. Bỏ hẳn để tránh dead code.

@immutable
class WorkforceRun {
  final String runId;
  final String workspaceId;
  final String agentSpecId;
  final String agentSpecVersion;
  final String definitionHash;
  final String status;
  final DateTime createdAt;
  final DateTime? completedAt;
  final int? totalTokens;
  final String? errorMessage;

  const WorkforceRun({
    required this.runId,
    required this.workspaceId,
    required this.agentSpecId,
    required this.agentSpecVersion,
    required this.definitionHash,
    required this.status,
    required this.createdAt,
    this.completedAt,
    this.totalTokens,
    this.errorMessage,
  });

  factory WorkforceRun.fromJson(Map<String, dynamic> json) {
    return WorkforceRun(
      runId: json['run_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      agentSpecId: json['agent_spec_id'] as String? ?? '',
      agentSpecVersion: json['agent_spec_version'] as String? ?? '',
      definitionHash: json['definition_hash'] as String? ?? '',
      status: json['status'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      totalTokens: json['total_tokens'] as int?,
      errorMessage: json['error_message'] as String?,
    );
  }
}

@immutable
class WorkforceRunEvent {
  final String eventId;
  final String runId;
  final int sequence;
  final String eventType;
  final Map<String, dynamic> payload;
  final DateTime createdAt;

  const WorkforceRunEvent({
    required this.eventId,
    required this.runId,
    required this.sequence,
    required this.eventType,
    required this.payload,
    required this.createdAt,
  });

  factory WorkforceRunEvent.fromJson(Map<String, dynamic> json) {
    return WorkforceRunEvent(
      eventId: json['event_id'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      sequence: json['sequence'] as int? ?? 0,
      eventType: json['event_type'] as String? ?? '',
      payload: (json['payload'] as Map?)?.cast<String, dynamic>() ?? const {},
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceApproval {
  final String approvalId;
  final String runId;
  final String? toolCallId;
  final String? checkpointRef;
  final String action;
  final String subject;
  final String status;
  final String riskLevel;
  final String requiredRole;
  final String policyId;
  final DateTime createdAt;

  const WorkforceApproval({
    required this.approvalId,
    required this.runId,
    this.toolCallId,
    this.checkpointRef,
    required this.action,
    required this.subject,
    required this.status,
    required this.riskLevel,
    required this.requiredRole,
    required this.policyId,
    required this.createdAt,
  });

  factory WorkforceApproval.fromJson(Map<String, dynamic> json) {
    return WorkforceApproval(
      approvalId: json['approval_id'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      toolCallId: json['tool_call_id'] as String?,
      checkpointRef: json['checkpoint_ref'] as String?,
      action: json['action'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      status: json['status'] as String? ?? '',
      riskLevel: json['risk_level'] as String? ?? 'medium',
      requiredRole: json['required_role'] as String? ?? 'admin',
      policyId: json['policy_id'] as String? ?? 'default',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceApprovalDecision {
  final String approvalId;
  final String runId;
  final String status;
  final String? reviewer;
  final String? reason;
  final DateTime decidedAt;

  const WorkforceApprovalDecision({
    required this.approvalId,
    required this.runId,
    required this.status,
    this.reviewer,
    this.reason,
    required this.decidedAt,
  });

  factory WorkforceApprovalDecision.fromJson(Map<String, dynamic> json) {
    return WorkforceApprovalDecision(
      approvalId: json['approval_id'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      reviewer: json['reviewer'] as String?,
      reason: json['reason'] as String?,
      decidedAt: DateTime.tryParse(json['decided_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceCompositionEntry {
  final String functionalKey;
  final String title;
  final String description;
  final String specId;
  final String specVersion;
  final String definitionHash;
  final List<String> allowedCapabilityPrefixes;
  final bool assigned;
  final String? assignmentId;
  final String? status;
  final List<String> eligibilityReasons;

  const WorkforceCompositionEntry({
    required this.functionalKey,
    required this.title,
    required this.description,
    required this.specId,
    required this.specVersion,
    required this.definitionHash,
    required this.allowedCapabilityPrefixes,
    required this.assigned,
    this.assignmentId,
    this.status,
    required this.eligibilityReasons,
  });

  factory WorkforceCompositionEntry.fromJson(Map<String, dynamic> json) {
    return WorkforceCompositionEntry(
      functionalKey: json['functional_key'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      specId: json['spec_id'] as String? ?? '',
      specVersion: json['spec_version'] as String? ?? '',
      definitionHash: json['definition_hash'] as String? ?? '',
      allowedCapabilityPrefixes:
          (json['allowed_capability_prefixes'] as List?)?.cast<String>() ?? const [],
      assigned: json['assigned'] as bool? ?? false,
      assignmentId: json['assignment_id'] as String?,
      status: json['status'] as String?,
      eligibilityReasons: (json['eligibility_reasons'] as List?)?.cast<String>() ?? const [],
    );
  }
}

@immutable
class WorkforceRosterEntry {
  final int id;
  final String key;
  final String name;
  final String roleTitle;
  final String department;
  final String agentType;
  final String defaultModelProfile;
  final int riskLevel;
  final String status;
  final bool enabled;

  const WorkforceRosterEntry({
    required this.id,
    required this.key,
    required this.name,
    required this.roleTitle,
    required this.department,
    required this.agentType,
    required this.defaultModelProfile,
    required this.riskLevel,
    required this.status,
    required this.enabled,
  });

  factory WorkforceRosterEntry.fromJson(Map<String, dynamic> json) {
    return WorkforceRosterEntry(
      id: json['id'] as int? ?? 0,
      key: json['key'] as String? ?? '',
      name: json['name'] as String? ?? '',
      roleTitle: json['role_title'] as String? ?? '',
      department: json['department'] as String? ?? '',
      agentType: json['agent_type'] as String? ?? '',
      defaultModelProfile: json['default_model_profile'] as String? ?? '',
      riskLevel: json['risk_level'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
    );
  }
}

@immutable
class WorkforceWorkProduct {
  final String id;
  final String title;
  final String productType;
  final String status;
  final String authorAgentKey;
  final String objectRef;
  final DateTime createdAt;

  const WorkforceWorkProduct({
    required this.id,
    required this.title,
    required this.productType,
    required this.status,
    required this.authorAgentKey,
    required this.objectRef,
    required this.createdAt,
  });

  factory WorkforceWorkProduct.fromJson(Map<String, dynamic> json) {
    return WorkforceWorkProduct(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      productType: json['product_type'] as String? ?? '',
      status: json['status'] as String? ?? '',
      authorAgentKey: json['author_agent_key'] as String? ?? '',
      objectRef: json['object_ref'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceException {
  final String id;
  final String exceptionType;
  final String tier;
  final String status;
  final String agentKey;
  final DateTime createdAt;

  const WorkforceException({
    required this.id,
    required this.exceptionType,
    required this.tier,
    required this.status,
    required this.agentKey,
    required this.createdAt,
  });

  factory WorkforceException.fromJson(Map<String, dynamic> json) {
    return WorkforceException(
      id: json['id'] as String? ?? '',
      exceptionType: json['exception_type'] as String? ?? '',
      tier: json['tier'] as String? ?? '',
      status: json['status'] as String? ?? '',
      agentKey: json['agent_key'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceExceptionSummary {
  final int total;
  final int founderGateCount;
  final int leadNotifyCount;
  final bool hasCritical;
  final List<WorkforceException> escalations;

  const WorkforceExceptionSummary({
    required this.total,
    required this.founderGateCount,
    required this.leadNotifyCount,
    required this.hasCritical,
    required this.escalations,
  });

  factory WorkforceExceptionSummary.fromJson(Map<String, dynamic> json) {
    final rawList = json['escalations'] as List? ?? const [];
    return WorkforceExceptionSummary(
      total: json['total'] as int? ?? 0,
      founderGateCount: json['founder_gate_count'] as int? ?? 0,
      leadNotifyCount: json['lead_notify_count'] as int? ?? 0,
      hasCritical: json['has_critical'] as bool? ?? false,
      escalations: rawList
          .whereType<Map<String, dynamic>>()
          .map(WorkforceException.fromJson)
          .toList(),
    );
  }
}

@immutable
class WorkforceStageRosterTask {
  final String taskId;
  final String title;
  final String priority;
  final String status;
  final String projectId;

  const WorkforceStageRosterTask({
    required this.taskId,
    required this.title,
    required this.priority,
    required this.status,
    required this.projectId,
  });

  factory WorkforceStageRosterTask.fromJson(Map<String, dynamic> json) {
    return WorkforceStageRosterTask(
      taskId: json['task_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      priority: json['priority'] as String? ?? '',
      status: json['status'] as String? ?? '',
      projectId: json['project_id'] as String? ?? '',
    );
  }
}

@immutable
class WorkforceStageRosterSummary {
  final int total;
  final int highPriority;
  final int medium;
  final int locked;

  const WorkforceStageRosterSummary({
    required this.total,
    required this.highPriority,
    required this.medium,
    required this.locked,
  });

  factory WorkforceStageRosterSummary.fromJson(Map<String, dynamic> json) {
    return WorkforceStageRosterSummary(
      total: json['total'] as int? ?? 0,
      highPriority: json['high_priority'] as int? ?? 0,
      medium: json['medium'] as int? ?? 0,
      locked: json['locked'] as int? ?? 0,
    );
  }
}

@immutable
class WorkforceStageRosterStage {
  final String stageCode;
  final int taskCount;

  const WorkforceStageRosterStage({required this.stageCode, required this.taskCount});

  factory WorkforceStageRosterStage.fromJson(Map<String, dynamic> json) {
    return WorkforceStageRosterStage(
      stageCode: json['stage_code'] as String? ?? '',
      taskCount: json['task_count'] as int? ?? 0,
    );
  }
}

@immutable
class WorkforceStageRoster {
  final WorkforceStageRosterStage stage;
  final List<WorkforceStageRosterTask> roster;
  final WorkforceStageRosterSummary summary;

  const WorkforceStageRoster({required this.stage, required this.roster, required this.summary});

  factory WorkforceStageRoster.fromJson(Map<String, dynamic> json) {
    final rawRoster = json['roster'] as List? ?? const [];
    return WorkforceStageRoster(
      stage: WorkforceStageRosterStage.fromJson(json['stage'] as Map<String, dynamic>? ?? const {}),
      roster: rawRoster
          .whereType<Map<String, dynamic>>()
          .map(WorkforceStageRosterTask.fromJson)
          .toList(),
      summary: WorkforceStageRosterSummary.fromJson(json['summary'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

@immutable
class WorkforceDashboardSummary {
  final int rosterTotal;
  final int rosterActive;
  final int openExceptions;
  final int pendingApprovals;
  final int workProductsTotal;

  const WorkforceDashboardSummary({
    required this.rosterTotal,
    required this.rosterActive,
    required this.openExceptions,
    required this.pendingApprovals,
    required this.workProductsTotal,
  });

  factory WorkforceDashboardSummary.fromJson(Map<String, dynamic> json) {
    return WorkforceDashboardSummary(
      rosterTotal: json['roster_total'] as int? ?? 0,
      rosterActive: json['roster_active'] as int? ?? 0,
      openExceptions: json['open_exceptions'] as int? ?? 0,
      pendingApprovals: json['pending_approvals'] as int? ?? 0,
      workProductsTotal: json['work_products_total'] as int? ?? 0,
    );
  }
}
