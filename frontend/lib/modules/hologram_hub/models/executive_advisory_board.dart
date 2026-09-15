import 'package:flutter/foundation.dart';

/// Trạng thái office của Role ở phạm vi Workspace (một office duy nhất).
enum ExecutiveOfficeState {
  active,
  disabled,
  availableNotActivated,
  unavailable;

  static ExecutiveOfficeState fromString(String val) {
    switch (val.toUpperCase()) {
      case 'ACTIVE':
        return ExecutiveOfficeState.active;
      case 'DISABLED':
        return ExecutiveOfficeState.disabled;
      case 'AVAILABLE_NOT_ACTIVATED':
        return ExecutiveOfficeState.availableNotActivated;
      case 'UNAVAILABLE':
        return ExecutiveOfficeState.unavailable;
      default:
        throw FormatException('Unknown Executive Office state: $val');
    }
  }
}

/// Trạng thái deploy Workspace Agent vào Project cụ thể.
enum ExecutiveProjectDeploymentState {
  active,
  inactive,
  paused,
  retired;

  static ExecutiveProjectDeploymentState fromString(String val) {
    switch (val.toUpperCase()) {
      case 'ACTIVE':
        return ExecutiveProjectDeploymentState.active;
      case 'PAUSED':
        return ExecutiveProjectDeploymentState.paused;
      case 'RETIRED':
        return ExecutiveProjectDeploymentState.retired;
      case 'INACTIVE':
        return ExecutiveProjectDeploymentState.inactive;
      default:
        throw FormatException('Unknown Project deployment state: $val');
    }
  }
}

enum ExecutiveStageEligibility {
  allowed,
  notSuggested;

  static ExecutiveStageEligibility fromString(String val) {
    switch (val.toUpperCase()) {
      case 'ALLOWED':
        return ExecutiveStageEligibility.allowed;
      case 'NOT_SUGGESTED':
        return ExecutiveStageEligibility.notSuggested;
      default:
        throw FormatException('Unknown Executive stage eligibility: $val');
    }
  }
}

/// Trạng thái tư vấn hiệu lực tổng hợp cho Project hiện tại.
enum ExecutiveEffectiveState {
  effective,
  officeDisabled,
  deploymentInactive,
  stageForbidden;

  static ExecutiveEffectiveState fromString(String val) {
    switch (val.toUpperCase()) {
      case 'EFFECTIVE':
        return ExecutiveEffectiveState.effective;
      case 'OFFICE_DISABLED':
        return ExecutiveEffectiveState.officeDisabled;
      case 'DEPLOYMENT_INACTIVE':
        return ExecutiveEffectiveState.deploymentInactive;
      case 'STAGE_FORBIDDEN':
        return ExecutiveEffectiveState.stageForbidden;
      default:
        throw FormatException('Unknown Executive effective state: $val');
    }
  }
}

@immutable
class ExecutiveAdvisorRole {
  final String roleKey;
  final String label;
  final String advisoryRemit;
  final String requiredProfileKey;
  final ExecutiveOfficeState officeState;
  final ExecutiveProjectDeploymentState projectDeploymentState;
  final ExecutiveStageEligibility stageEligibility;
  final ExecutiveEffectiveState effectiveState;
  final int workspaceOfficeVersion;
  final String? projectAgentDeploymentId;
  final String? disabledReason;

  const ExecutiveAdvisorRole({
    required this.roleKey,
    required this.label,
    required this.advisoryRemit,
    required this.requiredProfileKey,
    required this.officeState,
    required this.projectDeploymentState,
    required this.stageEligibility,
    required this.effectiveState,
    required this.workspaceOfficeVersion,
    this.projectAgentDeploymentId,
    this.disabledReason,
  });

  factory ExecutiveAdvisorRole.fromJson(Map<String, dynamic> json) {
    String requiredString(String field) {
      final value = json[field];
      if (value is! String || value.trim().isEmpty) {
        throw FormatException('Executive role $field is required');
      }
      return value;
    }

    final officeVersion = json['workspaceOfficeVersion'];
    if (officeVersion is! num ||
        officeVersion < 1 ||
        officeVersion != officeVersion.roundToDouble()) {
      throw const FormatException(
        'Executive role workspaceOfficeVersion must be a positive integer',
      );
    }

    return ExecutiveAdvisorRole(
      roleKey: requiredString('roleKey'),
      label: requiredString('label'),
      advisoryRemit: requiredString('advisoryRemit'),
      requiredProfileKey: requiredString('requiredProfileKey'),
      officeState: ExecutiveOfficeState.fromString(
        requiredString('officeState'),
      ),
      projectDeploymentState: ExecutiveProjectDeploymentState.fromString(
        requiredString('projectDeploymentState'),
      ),
      stageEligibility: ExecutiveStageEligibility.fromString(
        requiredString('stageEligibility'),
      ),
      effectiveState: ExecutiveEffectiveState.fromString(
        requiredString('effectiveState'),
      ),
      workspaceOfficeVersion: officeVersion.toInt(),
      projectAgentDeploymentId: json['projectAgentDeploymentId'] as String?,
      disabledReason: json['disabledReason'] as String?,
    );
  }
}

@immutable
class ExecutiveRoleMutationReceipt {
  final String id;
  final String roleKey;
  final String state;
  final int version;

  const ExecutiveRoleMutationReceipt({
    required this.id,
    required this.roleKey,
    required this.state,
    required this.version,
  });

  factory ExecutiveRoleMutationReceipt.fromJson(Map<String, dynamic> json) {
    return ExecutiveRoleMutationReceipt(
      id: json['id'] as String? ?? '',
      roleKey: json['roleKey'] as String? ?? '',
      state: json['state'] as String? ?? '',
      version: (json['version'] as num?)?.toInt() ?? 0,
    );
  }
}

@immutable
class DeliberationAnalysis {
  final String id;
  final int frameVersion;
  final String roleKey;
  final String runId;
  final String status;
  final Map<String, dynamic> descriptor;
  final DateTime createdAt;

  const DeliberationAnalysis({
    required this.id,
    required this.frameVersion,
    required this.roleKey,
    required this.runId,
    required this.status,
    required this.descriptor,
    required this.createdAt,
  });

  factory DeliberationAnalysis.fromJson(Map<String, dynamic> json) {
    return DeliberationAnalysis(
      id: json['id'] as String? ?? '',
      frameVersion: json['frameVersion'] as int? ?? 1,
      roleKey: json['roleKey'] as String? ?? '',
      runId: json['runId'] as String? ?? '',
      status: json['status'] as String? ?? 'COMPLETED',
      descriptor: (json['descriptor'] as Map<String, dynamic>?) ?? const {},
      createdAt: json['createdAt'] != null
          ? DateTime.tryParse(json['createdAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

@immutable
class ExecutiveDeliberation {
  final String id;
  final String workspaceId;
  final String projectId;
  final String title;
  final String state;
  final int activeFrameVersion;
  final int version;
  final String createdBy;
  final DateTime createdAt;
  final DateTime updatedAt;
  final Map<String, dynamic>? activeFrame;
  final Map<String, dynamic>? decision;
  final List<DeliberationAnalysis> analyses;

  const ExecutiveDeliberation({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.title,
    required this.state,
    required this.activeFrameVersion,
    required this.version,
    required this.createdBy,
    required this.createdAt,
    required this.updatedAt,
    this.activeFrame,
    this.decision,
    this.analyses = const [],
  });

  factory ExecutiveDeliberation.fromJson(Map<String, dynamic> json) {
    return ExecutiveDeliberation(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? '',
      projectId: json['projectId'] as String? ?? '',
      title: json['title'] as String? ?? '',
      state: json['state'] as String? ?? 'DRAFT',
      activeFrameVersion: json['activeFrameVersion'] as int? ?? 0,
      version: json['version'] as int? ?? 1,
      createdBy: json['createdBy'] as String? ?? '',
      createdAt: json['createdAt'] != null
          ? DateTime.tryParse(json['createdAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updatedAt'] != null
          ? DateTime.tryParse(json['updatedAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
      activeFrame: json['activeFrame'] as Map<String, dynamic>?,
      decision: json['decision'] as Map<String, dynamic>?,
      analyses:
          (json['analyses'] as List<dynamic>?)
              ?.map(
                (e) => DeliberationAnalysis.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          const [],
    );
  }
}
