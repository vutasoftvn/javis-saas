import 'package:flutter/foundation.dart';

// Task 3 — models chỉ decode đúng field mà backend contract
// (apps/cosa/api/workforce_schemas.py + workforce_routes.py) thực sự trả về.
// Không suy diễn thêm field không tồn tại trên response thật.

/// Kết quả tổng quát cho một thao tác Workforce — giữ theo đúng interface
/// trong task brief. `ApiResult<T>` (core/network/api_result.dart) đã đảm
/// nhiệm việc phân biệt success/failure cho mọi service; sealed class này
/// dự phòng cho consumer nào cần biểu diễn kết quả nghiệp vụ ở tầng cao hơn.
sealed class WorkforceResult<T> {
  const WorkforceResult();
}

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
