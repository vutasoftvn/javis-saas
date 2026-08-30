import 'package:flutter/material.dart';

enum PilotRunStatus {
  draft,
  approved,
  active,
  completed,
  cancelled;

  static PilotRunStatus fromString(String? val) {
    if (val == null) return PilotRunStatus.draft;
    final upper = val.toUpperCase().trim();
    switch (upper) {
      case 'DRAFT':
        return PilotRunStatus.draft;
      case 'APPROVED':
        return PilotRunStatus.approved;
      case 'ACTIVE':
        return PilotRunStatus.active;
      case 'COMPLETED':
        return PilotRunStatus.completed;
      case 'CANCELLED':
        return PilotRunStatus.cancelled;
      default:
        return PilotRunStatus.draft;
    }
  }

  String get labelVi {
    switch (this) {
      case PilotRunStatus.draft:
        return 'Bản Nháp (Draft)';
      case PilotRunStatus.approved:
        return 'Đã Phê Duyệt (Approved)';
      case PilotRunStatus.active:
        return 'Đang Hoạt Động (Active)';
      case PilotRunStatus.completed:
        return 'Hoàn Thành (Completed)';
      case PilotRunStatus.cancelled:
        return 'Đã Hủy (Cancelled)';
    }
  }

  Color get color {
    switch (this) {
      case PilotRunStatus.draft:
        return const Color(0xFF94A3B8);
      case PilotRunStatus.approved:
        return const Color(0xFF38BDF8);
      case PilotRunStatus.active:
        return const Color(0xFF10B981);
      case PilotRunStatus.completed:
        return const Color(0xFF6366F1);
      case PilotRunStatus.cancelled:
        return const Color(0xFFEF4444);
    }
  }
}

class PilotRun {
  final String id;
  final String workspaceId;
  final String projectId;
  final String? experimentId;
  final PilotRunStatus status;
  final List<String> designPartnerEvidenceRefs;
  final String? metricContractArtifactRef;
  final String? instrumentationArtifactRef;
  final String? onboardingArtifactRef;
  final String? supportEscalationArtifactRef;
  final String? rollbackArtifactRef;
  final String releaseOwnerMemberId;
  final String? approvedByMemberId;
  final String? approvalRef;
  final DateTime? approvedAt;
  final String? activatedByMemberId;
  final DateTime? activatedAt;
  final DateTime? completedAt;
  final DateTime? cancelledAt;
  final String? cancellationReason;
  final int version;
  final DateTime createdAt;
  final DateTime updatedAt;

  PilotRun({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.experimentId,
    required this.status,
    required this.designPartnerEvidenceRefs,
    this.metricContractArtifactRef,
    this.instrumentationArtifactRef,
    this.onboardingArtifactRef,
    this.supportEscalationArtifactRef,
    this.rollbackArtifactRef,
    required this.releaseOwnerMemberId,
    this.approvedByMemberId,
    this.approvalRef,
    this.approvedAt,
    this.activatedByMemberId,
    this.activatedAt,
    this.completedAt,
    this.cancelledAt,
    this.cancellationReason,
    required this.version,
    required this.createdAt,
    required this.updatedAt,
  });

  List<String> get missingPrerequisites {
    final missing = <String>[];
    if (designPartnerEvidenceRefs.isEmpty) {
      missing.add('Thiếu design partner evidence đã duyệt');
    }
    if (metricContractArtifactRef == null || metricContractArtifactRef!.trim().isEmpty) {
      missing.add('Thiếu metric contract');
    }
    if (instrumentationArtifactRef == null || instrumentationArtifactRef!.trim().isEmpty) {
      missing.add('Thiếu instrumentation plan');
    }
    if (onboardingArtifactRef == null || onboardingArtifactRef!.trim().isEmpty) {
      missing.add('Thiếu onboarding runbook');
    }
    if (rollbackArtifactRef == null || rollbackArtifactRef!.trim().isEmpty) {
      missing.add('Thiếu rollback runbook');
    }
    if (releaseOwnerMemberId.trim().isEmpty) {
      missing.add('Thiếu release owner');
    }
    return missing;
  }

  bool get isReadyForHumanApproval => missingPrerequisites.isEmpty && status == PilotRunStatus.draft;
  bool get isApproved => status == PilotRunStatus.approved;
  bool get isActive => status == PilotRunStatus.active;
  bool get isTerminal => status == PilotRunStatus.completed || status == PilotRunStatus.cancelled;

  factory PilotRun.fromJson(Map<String, dynamic> json) {
    final evidenceRefs = (json['designPartnerEvidenceRefs'] as List? ?? json['design_partner_evidence_refs'] as List? ?? [])
        .map((e) => e.toString())
        .toList();

    return PilotRun(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? json['workspace_id']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? json['project_id']?.toString() ?? '',
      experimentId: json['experimentId']?.toString() ?? json['experiment_id']?.toString(),
      status: PilotRunStatus.fromString(json['status']?.toString()),
      designPartnerEvidenceRefs: evidenceRefs,
      metricContractArtifactRef: json['metricContractArtifactRef']?.toString() ?? json['metric_contract_artifact_ref']?.toString(),
      instrumentationArtifactRef: json['instrumentationArtifactRef']?.toString() ?? json['instrumentation_artifact_ref']?.toString(),
      onboardingArtifactRef: json['onboardingArtifactRef']?.toString() ?? json['onboarding_artifact_ref']?.toString(),
      supportEscalationArtifactRef: json['supportEscalationArtifactRef']?.toString() ?? json['support_escalation_artifact_ref']?.toString(),
      rollbackArtifactRef: json['rollbackArtifactRef']?.toString() ?? json['rollback_artifact_ref']?.toString(),
      releaseOwnerMemberId: json['releaseOwnerMemberId']?.toString() ?? json['release_owner_member_id']?.toString() ?? '',
      approvedByMemberId: json['approvedByMemberId']?.toString() ?? json['approved_by_member_id']?.toString(),
      approvalRef: json['approvalRef']?.toString() ?? json['approval_ref']?.toString(),
      approvedAt: json['approvedAt'] != null || json['approved_at'] != null
          ? DateTime.tryParse((json['approvedAt'] ?? json['approved_at']).toString())
          : null,
      activatedByMemberId: json['activatedByMemberId']?.toString() ?? json['activated_by_member_id']?.toString(),
      activatedAt: json['activatedAt'] != null || json['activated_at'] != null
          ? DateTime.tryParse((json['activatedAt'] ?? json['activated_at']).toString())
          : null,
      completedAt: json['completedAt'] != null || json['completed_at'] != null
          ? DateTime.tryParse((json['completedAt'] ?? json['completed_at']).toString())
          : null,
      cancelledAt: json['cancelledAt'] != null || json['cancelled_at'] != null
          ? DateTime.tryParse((json['cancelledAt'] ?? json['cancelled_at']).toString())
          : null,
      cancellationReason: json['cancellationReason']?.toString() ?? json['cancellation_reason']?.toString(),
      version: int.tryParse(json['version']?.toString() ?? '') ?? 1,
      createdAt: json['createdAt'] != null || json['created_at'] != null
          ? DateTime.tryParse((json['createdAt'] ?? json['created_at']).toString()) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updatedAt'] != null || json['updated_at'] != null
          ? DateTime.tryParse((json['updatedAt'] ?? json['updated_at']).toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'projectId': projectId,
      'experimentId': experimentId,
      'status': status.name.toUpperCase(),
      'designPartnerEvidenceRefs': designPartnerEvidenceRefs,
      'metricContractArtifactRef': metricContractArtifactRef,
      'instrumentationArtifactRef': instrumentationArtifactRef,
      'onboardingArtifactRef': onboardingArtifactRef,
      'supportEscalationArtifactRef': supportEscalationArtifactRef,
      'rollbackArtifactRef': rollbackArtifactRef,
      'releaseOwnerMemberId': releaseOwnerMemberId,
      'approvedByMemberId': approvedByMemberId,
      'approvalRef': approvalRef,
      'approvedAt': approvedAt?.toIso8601String(),
      'activatedByMemberId': activatedByMemberId,
      'activatedAt': activatedAt?.toIso8601String(),
      'completedAt': completedAt?.toIso8601String(),
      'cancelledAt': cancelledAt?.toIso8601String(),
      'cancellationReason': cancellationReason,
      'version': version,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }
}
