import 'package:flutter/foundation.dart';

enum ExecutiveActivationState {
  unavailable,
  availableNotActivated,
  active,
  disabled;

  static ExecutiveActivationState fromString(String val) {
    switch (val.toUpperCase()) {
      case 'ACTIVE':
        return ExecutiveActivationState.active;
      case 'DISABLED':
        return ExecutiveActivationState.disabled;
      case 'AVAILABLE_NOT_ACTIVATED':
        return ExecutiveActivationState.availableNotActivated;
      case 'UNAVAILABLE':
      default:
        return ExecutiveActivationState.unavailable;
    }
  }

  String toWireString() {
    switch (this) {
      case ExecutiveActivationState.active:
        return 'ACTIVE';
      case ExecutiveActivationState.disabled:
        return 'DISABLED';
      case ExecutiveActivationState.availableNotActivated:
        return 'AVAILABLE_NOT_ACTIVATED';
      case ExecutiveActivationState.unavailable:
        return 'UNAVAILABLE';
    }
  }
}

@immutable
class ExecutiveAdvisorRole {
  final String roleKey;
  final String title;
  final String domain;
  final String advisoryLevel;
  final String description;
  final List<String> capabilities;
  final ExecutiveActivationState activationState;
  final String underlyingProfileKey;
  final String assignmentStatus;
  final String specHash;
  final String? disabledReason;
  final int? assignmentVersion;
  final DateTime? activatedAt;
  final String? activatedBy;

  const ExecutiveAdvisorRole({
    required this.roleKey,
    required this.title,
    required this.domain,
    required this.advisoryLevel,
    required this.description,
    required this.capabilities,
    required this.activationState,
    required this.underlyingProfileKey,
    required this.assignmentStatus,
    required this.specHash,
    this.disabledReason,
    this.assignmentVersion,
    this.activatedAt,
    this.activatedBy,
  });

  factory ExecutiveAdvisorRole.fromJson(Map<String, dynamic> json) {
    return ExecutiveAdvisorRole(
      roleKey: json['roleKey'] as String? ?? '',
      title: json['label'] as String? ?? json['title'] as String? ?? '',
      domain: json['requiredProfileKey'] as String? ?? json['domain'] as String? ?? '',
      advisoryLevel: json['advisoryLevel'] as String? ?? 'L1',
      description: json['advisoryRemit'] as String? ?? json['description'] as String? ?? '',
      capabilities: (json['capabilities'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      activationState: ExecutiveActivationState.fromString(
        json['displayState'] as String? ?? json['activationState'] as String? ?? '',
      ),
      underlyingProfileKey: json['requiredProfileKey'] as String? ?? json['underlyingProfileKey'] as String? ?? '',
      assignmentStatus: json['assignmentStatus'] as String? ?? '',
      specHash: json['specHash'] as String? ?? '',
      disabledReason: json['disabledReason'] as String?,
      assignmentVersion: (json['version'] as num?)?.toInt() ?? json['assignmentVersion'] as int?,
      activatedAt: json['activatedAt'] != null
          ? DateTime.tryParse(json['activatedAt'].toString())
          : null,
      activatedBy: json['activatedBy'] as String? ?? json['actorId'] as String?,
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
      analyses: (json['analyses'] as List<dynamic>?)
              ?.map((e) => DeliberationAnalysis.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }
}
