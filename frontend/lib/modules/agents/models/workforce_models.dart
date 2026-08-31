import 'package:flutter/foundation.dart';

@immutable
class WorkforceAssignment {
  final String assignmentId;
  final String workspaceId;
  final String functionalKey;
  final String specId;
  final String specVersion;
  final String definitionHash;
  final String? reportsToAssignmentId;
  final String configuredBy;
  final String status;
  final DateTime createdAt;
  final DateTime? retiredAt;

  const WorkforceAssignment({
    required this.assignmentId,
    required this.workspaceId,
    required this.functionalKey,
    required this.specId,
    required this.specVersion,
    required this.definitionHash,
    this.reportsToAssignmentId,
    required this.configuredBy,
    required this.status,
    required this.createdAt,
    this.retiredAt,
  });

  factory WorkforceAssignment.fromJson(Map<String, dynamic> json) {
    return WorkforceAssignment(
      assignmentId: json['assignment_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      functionalKey: json['functional_key'] as String? ?? '',
      specId: json['spec_id'] as String? ?? '',
      specVersion: json['spec_version'] as String? ?? '',
      definitionHash: json['definition_hash'] as String? ?? '',
      reportsToAssignmentId: json['reports_to_assignment_id'] as String?,
      configuredBy: json['configured_by'] as String? ?? '',
      status: json['status'] as String? ?? 'ACTIVE',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      retiredAt: json['retired_at'] != null ? DateTime.tryParse(json['retired_at'] as String) : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'assignment_id': assignmentId,
    'workspace_id': workspaceId,
    'functional_key': functionalKey,
    'spec_id': specId,
    'spec_version': specVersion,
    'definition_hash': definitionHash,
    'reports_to_assignment_id': reportsToAssignmentId,
    'configured_by': configuredBy,
    'status': status,
    'created_at': createdAt.toIso8601String(),
    'retired_at': retiredAt?.toIso8601String(),
  };
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
    this.eligibilityReasons = const [],
  });

  factory WorkforceCompositionEntry.fromJson(Map<String, dynamic> json) {
    return WorkforceCompositionEntry(
      functionalKey: json['functional_key'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      specId: json['spec_id'] as String? ?? '',
      specVersion: json['spec_version'] as String? ?? '',
      definitionHash: json['definition_hash'] as String? ?? '',
      allowedCapabilityPrefixes: (json['allowed_capability_prefixes'] as List?)?.map((e) => e.toString()).toList() ?? [],
      assigned: json['assigned'] as bool? ?? false,
      assignmentId: json['assignment_id'] as String?,
      status: json['status'] as String?,
      eligibilityReasons: (json['eligibility_reasons'] as List?)?.map((e) => e.toString()).toList() ?? [],
    );
  }
}

@immutable
class WorkforceOrgChartNode {
  final String assignmentId;
  final String functionalKey;
  final String specId;
  final String status;
  final String? reportsToAssignmentId;
  final List<WorkforceOrgChartNode> directReports;

  const WorkforceOrgChartNode({
    required this.assignmentId,
    required this.functionalKey,
    required this.specId,
    required this.status,
    this.reportsToAssignmentId,
    this.directReports = const [],
  });

  factory WorkforceOrgChartNode.fromJson(Map<String, dynamic> json) {
    return WorkforceOrgChartNode(
      assignmentId: json['assignment_id'] as String? ?? '',
      functionalKey: json['functional_key'] as String? ?? '',
      specId: json['spec_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      reportsToAssignmentId: json['reports_to_assignment_id'] as String?,
      directReports: (json['direct_reports'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map((e) => WorkforceOrgChartNode.fromJson(e))
              .toList() ??
          [],
    );
  }
}

@immutable
class WorkforceOrgChart {
  final List<WorkforceOrgChartNode> roots;
  final int totalAssignments;

  const WorkforceOrgChart({
    required this.roots,
    required this.totalAssignments,
  });

  factory WorkforceOrgChart.fromJson(Map<String, dynamic> json) {
    return WorkforceOrgChart(
      roots: (json['roots'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map((e) => WorkforceOrgChartNode.fromJson(e))
              .toList() ??
          [],
      totalAssignments: json['total_assignments'] as int? ?? 0,
    );
  }
}

@immutable
class WorkforceCapability {
  final String capabilityRef;
  final String functionalKey;
  final String specId;
  final String specVersion;
  final String status;

  const WorkforceCapability({
    required this.capabilityRef,
    required this.functionalKey,
    required this.specId,
    required this.specVersion,
    required this.status,
  });

  factory WorkforceCapability.fromJson(Map<String, dynamic> json) {
    return WorkforceCapability(
      capabilityRef: json['capability_ref'] as String? ?? '',
      functionalKey: json['functional_key'] as String? ?? '',
      specId: json['spec_id'] as String? ?? '',
      specVersion: json['spec_version'] as String? ?? '',
      status: json['status'] as String? ?? 'ENABLED',
    );
  }
}

@immutable
class WorkforceCostObservation {
  final String observationId;
  final String workspaceId;
  final String runId;
  final String providerKey;
  final String modelKey;
  final int? inputTokens;
  final int? outputTokens;
  final double? costAmount;
  final String? currency;
  final DateTime observedAt;

  const WorkforceCostObservation({
    required this.observationId,
    required this.workspaceId,
    required this.runId,
    required this.providerKey,
    required this.modelKey,
    this.inputTokens,
    this.outputTokens,
    this.costAmount,
    this.currency,
    required this.observedAt,
  });

  factory WorkforceCostObservation.fromJson(Map<String, dynamic> json) {
    return WorkforceCostObservation(
      observationId: json['observation_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      providerKey: json['provider_key'] as String? ?? '',
      modelKey: json['model_key'] as String? ?? '',
      inputTokens: json['input_tokens'] as int?,
      outputTokens: json['output_tokens'] as int?,
      costAmount: (json['cost_amount'] as num?)?.toDouble(),
      currency: json['currency'] as String?,
      observedAt: DateTime.tryParse(json['observed_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceHealth {
  final String assignmentId;
  final String functionalKey;
  final String status;
  final DateTime? observedAt;
  final String? sourceRef;
  final String? lastRunId;
  final String? message;

  const WorkforceHealth({
    required this.assignmentId,
    required this.functionalKey,
    required this.status,
    this.observedAt,
    this.sourceRef,
    this.lastRunId,
    this.message,
  });

  factory WorkforceHealth.fromJson(Map<String, dynamic> json) {
    return WorkforceHealth(
      assignmentId: json['assignment_id'] as String? ?? '',
      functionalKey: json['functional_key'] as String? ?? '',
      status: json['status'] as String? ?? 'not_observed',
      observedAt: json['observed_at'] != null ? DateTime.tryParse(json['observed_at'] as String) : null,
      sourceRef: json['source_ref'] as String?,
      lastRunId: json['last_run_id'] as String?,
      message: json['message'] as String?,
    );
  }
}

@immutable
class WorkforceRunSummary {
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

  const WorkforceRunSummary({
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

  factory WorkforceRunSummary.fromJson(Map<String, dynamic> json) {
    return WorkforceRunSummary(
      runId: json['run_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      agentSpecId: json['agent_spec_id'] as String? ?? '',
      agentSpecVersion: json['agent_spec_version'] as String? ?? '',
      definitionHash: json['definition_hash'] as String? ?? '',
      status: json['status'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      completedAt: json['completed_at'] != null ? DateTime.tryParse(json['completed_at'] as String) : null,
      totalTokens: json['total_tokens'] as int?,
      errorMessage: json['error_message'] as String?,
    );
  }
}

@immutable
class WorkforceRunDetail {
  final String runId;
  final String workspaceId;
  final String agentSpecId;
  final String agentSpecVersion;
  final String definitionHash;
  final String status;
  final DateTime createdAt;
  final DateTime? completedAt;
  final Map<String, dynamic> inputPayload;
  final Map<String, dynamic>? outputPayload;
  final String? errorMessage;

  const WorkforceRunDetail({
    required this.runId,
    required this.workspaceId,
    required this.agentSpecId,
    required this.agentSpecVersion,
    required this.definitionHash,
    required this.status,
    required this.createdAt,
    this.completedAt,
    required this.inputPayload,
    this.outputPayload,
    this.errorMessage,
  });

  factory WorkforceRunDetail.fromJson(Map<String, dynamic> json) {
    return WorkforceRunDetail(
      runId: json['run_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      agentSpecId: json['agent_spec_id'] as String? ?? '',
      agentSpecVersion: json['agent_spec_version'] as String? ?? '',
      definitionHash: json['definition_hash'] as String? ?? '',
      status: json['status'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      completedAt: json['completed_at'] != null ? DateTime.tryParse(json['completed_at'] as String) : null,
      inputPayload: json['input_payload'] as Map<String, dynamic>? ?? {},
      outputPayload: json['output_payload'] as Map<String, dynamic>?,
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
      payload: json['payload'] as Map<String, dynamic>? ?? {},
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceRunArtifact {
  final String artifactId;
  final String runId;
  final String artifactType;
  final String uri;
  final DateTime createdAt;

  const WorkforceRunArtifact({
    required this.artifactId,
    required this.runId,
    required this.artifactType,
    required this.uri,
    required this.createdAt,
  });

  factory WorkforceRunArtifact.fromJson(Map<String, dynamic> json) {
    return WorkforceRunArtifact(
      artifactId: json['artifact_id'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      artifactType: json['artifact_type'] as String? ?? '',
      uri: json['uri'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceSchedule {
  final String scheduleId;
  final String workspaceId;
  final String name;
  final String functionalKey;
  final String cronExpression;
  final String status;
  final DateTime? nextRunAt;
  final DateTime createdAt;

  const WorkforceSchedule({
    required this.scheduleId,
    required this.workspaceId,
    required this.name,
    required this.functionalKey,
    required this.cronExpression,
    required this.status,
    this.nextRunAt,
    required this.createdAt,
  });

  factory WorkforceSchedule.fromJson(Map<String, dynamic> json) {
    return WorkforceSchedule(
      scheduleId: json['schedule_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      functionalKey: json['functional_key'] as String? ?? '',
      cronExpression: json['cron_expression'] as String? ?? '',
      status: json['status'] as String? ?? 'ACTIVE',
      nextRunAt: json['next_run_at'] != null ? DateTime.tryParse(json['next_run_at'] as String) : null,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceApproval {
  final String approvalId;
  final String workspaceId;
  final String runId;
  final String capabilityRef;
  final String actionClass;
  final String status;
  final DateTime requestedAt;
  final DateTime? decidedAt;
  final String? decision;
  final String? reason;

  const WorkforceApproval({
    required this.approvalId,
    required this.workspaceId,
    required this.runId,
    required this.capabilityRef,
    required this.actionClass,
    required this.status,
    required this.requestedAt,
    this.decidedAt,
    this.decision,
    this.reason,
  });

  factory WorkforceApproval.fromJson(Map<String, dynamic> json) {
    return WorkforceApproval(
      approvalId: json['approval_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      capabilityRef: json['capability_ref'] as String? ?? '',
      actionClass: json['action_class'] as String? ?? 'B',
      status: json['status'] as String? ?? 'PENDING',
      requestedAt: DateTime.tryParse(json['requested_at'] as String? ?? '') ?? DateTime.now(),
      decidedAt: json['decided_at'] != null ? DateTime.tryParse(json['decided_at'] as String) : null,
      decision: json['decision'] as String?,
      reason: json['reason'] as String?,
    );
  }
}

@immutable
class WorkforceApprovalDecision {
  final String approvalId;
  final String status;
  final DateTime decidedAt;
  final String? reason;

  const WorkforceApprovalDecision({
    required this.approvalId,
    required this.status,
    required this.decidedAt,
    this.reason,
  });

  factory WorkforceApprovalDecision.fromJson(Map<String, dynamic> json) {
    return WorkforceApprovalDecision(
      approvalId: json['approval_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      decidedAt: DateTime.tryParse(json['decided_at'] as String? ?? '') ?? DateTime.now(),
      reason: json['reason'] as String?,
    );
  }
}
