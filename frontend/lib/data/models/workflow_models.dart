import 'package:flutter/foundation.dart';

@immutable
class WorkflowDefinitionModel {
  final String id;
  final String name;
  final String description;
  final List<String> stepNames;
  final String triggerType; // 'manual', 'event', 'cron'
  final bool hasApprovalGate;

  const WorkflowDefinitionModel({
    required this.id,
    required this.name,
    this.description = '',
    this.stepNames = const [],
    this.triggerType = 'manual',
    this.hasApprovalGate = false,
  });

  factory WorkflowDefinitionModel.fromJson(Map<String, dynamic> json) {
    final rawSteps = json['steps'] ?? json['step_names'] ?? [];
    final steps = rawSteps is List ? rawSteps.map((e) => e.toString()).toList() : <String>[];
    return WorkflowDefinitionModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      stepNames: steps,
      triggerType: json['trigger_type']?.toString() ?? 'manual',
      hasApprovalGate: json['has_approval_gate'] == true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'step_names': stepNames,
      'trigger_type': triggerType,
      'has_approval_gate': hasApprovalGate,
    };
  }
}

@immutable
class WorkflowRunModel {
  final String id;
  final String workflowId;
  final String status; // 'PENDING', 'RUNNING', 'WAITING_APPROVAL', 'COMPLETED', 'FAILED', 'CANCELLED'
  final int currentStepIndex;
  final Map<String, dynamic> state;
  final String? pendingApprovalId;
  final String? error;
  final DateTime createdAt;

  const WorkflowRunModel({
    required this.id,
    required this.workflowId,
    required this.status,
    this.currentStepIndex = 0,
    this.state = const {},
    this.pendingApprovalId,
    this.error,
    required this.createdAt,
  });

  factory WorkflowRunModel.fromJson(Map<String, dynamic> json) {
    return WorkflowRunModel(
      id: json['id']?.toString() ?? '',
      workflowId: json['workflow_id']?.toString() ?? json['definition_id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PENDING',
      currentStepIndex: (json['current_step_index'] as num?)?.toInt() ?? 0,
      state: json['state'] is Map ? Map<String, dynamic>.from(json['state'] as Map) : const {},
      pendingApprovalId: json['pending_approval_id']?.toString(),
      error: json['error']?.toString(),
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workflow_id': workflowId,
      'status': status,
      'current_step_index': currentStepIndex,
      'state': state,
      'pending_approval_id': pendingApprovalId,
      'error': error,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

@immutable
class ApprovalRequestModel {
  final String id;
  final String action;
  final String subject;
  final String requester;
  final String? runId;
  final String status; // 'PENDING', 'APPROVED', 'DENIED'
  final String? reviewer;
  final String? reason;
  final DateTime createdAt;
  final DateTime? decidedAt;

  const ApprovalRequestModel({
    required this.id,
    required this.action,
    required this.subject,
    required this.requester,
    this.runId,
    this.status = 'PENDING',
    this.reviewer,
    this.reason,
    required this.createdAt,
    this.decidedAt,
  });

  factory ApprovalRequestModel.fromJson(Map<String, dynamic> json) {
    return ApprovalRequestModel(
      id: json['id']?.toString() ?? '',
      action: json['action']?.toString() ?? '',
      subject: json['subject']?.toString() ?? '',
      requester: json['requester']?.toString() ?? '',
      runId: json['run_id']?.toString(),
      status: json['status']?.toString() ?? 'PENDING',
      reviewer: json['reviewer']?.toString(),
      reason: json['reason']?.toString(),
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      decidedAt: json['decided_at'] != null ? DateTime.tryParse(json['decided_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'action': action,
      'subject': subject,
      'requester': requester,
      'run_id': runId,
      'status': status,
      'reviewer': reviewer,
      'reason': reason,
      'created_at': createdAt.toIso8601String(),
      'decided_at': decidedAt?.toIso8601String(),
    };
  }
}
