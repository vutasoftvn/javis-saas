import 'package:flutter/material.dart';

enum ApprovalRiskLevel {
  critical,
  high,
  medium,
  low;

  static ApprovalRiskLevel fromString(String? val) {
    switch (val?.toString().toUpperCase()) {
      case 'CRITICAL':
        return ApprovalRiskLevel.critical;
      case 'HIGH':
        return ApprovalRiskLevel.high;
      case 'MEDIUM':
        return ApprovalRiskLevel.medium;
      case 'LOW':
        return ApprovalRiskLevel.low;
      default:
        return ApprovalRiskLevel.high;
    }
  }

  String get label {
    switch (this) {
      case ApprovalRiskLevel.critical:
        return 'CRITICAL';
      case ApprovalRiskLevel.high:
        return 'HIGH';
      case ApprovalRiskLevel.medium:
        return 'MEDIUM';
      case ApprovalRiskLevel.low:
        return 'LOW';
    }
  }

  Color get color {
    switch (this) {
      case ApprovalRiskLevel.critical:
        return const Color(0xFFEF4444);
      case ApprovalRiskLevel.high:
        return const Color(0xFFF97316);
      case ApprovalRiskLevel.medium:
        return const Color(0xFFF59E0B);
      case ApprovalRiskLevel.low:
        return const Color(0xFF10B981);
    }
  }
}

enum ApprovalStatus {
  pending,
  approved,
  rejected,
  cancelled;

  static ApprovalStatus fromString(String? val) {
    switch (val?.toString().toLowerCase()) {
      case 'approved':
        return ApprovalStatus.approved;
      case 'rejected':
        return ApprovalStatus.rejected;
      case 'cancelled':
        return ApprovalStatus.cancelled;
      case 'pending':
      default:
        return ApprovalStatus.pending;
    }
  }

  String get label {
    switch (this) {
      case ApprovalStatus.approved:
        return 'Đã chấp thuận';
      case ApprovalStatus.rejected:
        return 'Đã từ chối';
      case ApprovalStatus.cancelled:
        return 'Đã hủy';
      case ApprovalStatus.pending:
        return 'Chờ duyệt';
    }
  }
}

class ApprovalItemModel {
  final String id;
  final String title;
  final String? description;
  final String? actionType;
  final ApprovalRiskLevel riskLevel;
  final ApprovalStatus status;
  final String? requesterName;
  final String? agentId;
  final String? agentName;
  final String? workflowId;
  final String? workspaceId;
  final Map<String, dynamic> payload;
  final String? comment;
  final String? rejectionReason;
  final DateTime? createdAt;
  final DateTime? decidedAt;

  const ApprovalItemModel({
    required this.id,
    required this.title,
    this.description,
    this.actionType,
    this.riskLevel = ApprovalRiskLevel.high,
    this.status = ApprovalStatus.pending,
    this.requesterName,
    this.agentId,
    this.agentName,
    this.workflowId,
    this.workspaceId,
    this.payload = const {},
    this.comment,
    this.rejectionReason,
    this.createdAt,
    this.decidedAt,
  });

  factory ApprovalItemModel.fromJson(Map<String, dynamic> json) {
    return ApprovalItemModel(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? json['action_type']?.toString() ?? 'Yêu cầu phê duyệt',
      description: json['description']?.toString() ?? json['reason']?.toString(),
      actionType: json['action_type']?.toString(),
      riskLevel: ApprovalRiskLevel.fromString(json['risk_level']?.toString()),
      status: ApprovalStatus.fromString(json['status']?.toString()),
      requesterName: json['requester_name']?.toString() ?? json['requester']?.toString(),
      agentId: json['agent_id']?.toString(),
      agentName: json['agent_name']?.toString(),
      workflowId: json['workflow_id']?.toString(),
      workspaceId: json['workspace_id']?.toString(),
      payload: json['payload'] is Map<String, dynamic>
          ? json['payload'] as Map<String, dynamic>
          : {},
      comment: json['comment']?.toString(),
      rejectionReason: json['rejection_reason']?.toString(),
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      decidedAt: json['decided_at'] != null ? DateTime.tryParse(json['decided_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'action_type': actionType,
      'risk_level': riskLevel.label,
      'status': status.name,
      'requester_name': requesterName,
      'agent_id': agentId,
      'agent_name': agentName,
      'workflow_id': workflowId,
      'workspace_id': workspaceId,
      'payload': payload,
      'comment': comment,
      'rejection_reason': rejectionReason,
      'created_at': createdAt?.toIso8601String(),
      'decided_at': decidedAt?.toIso8601String(),
    };
  }
}
