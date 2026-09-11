enum TeamDisplayState {
  chatReady,
  template,
  active,
  paused,
  retired;

  static TeamDisplayState fromString(String val) {
    switch (val.toUpperCase()) {
      case 'CHAT_READY':
        return TeamDisplayState.chatReady;
      case 'ACTIVE':
        return TeamDisplayState.active;
      case 'PAUSED':
        return TeamDisplayState.paused;
      case 'RETIRED':
        return TeamDisplayState.retired;
      case 'TEMPLATE':
      default:
        return TeamDisplayState.template;
    }
  }

  String toWireString() {
    switch (this) {
      case TeamDisplayState.chatReady:
        return 'CHAT_READY';
      case TeamDisplayState.active:
        return 'ACTIVE';
      case TeamDisplayState.paused:
        return 'PAUSED';
      case TeamDisplayState.retired:
        return 'RETIRED';
      case TeamDisplayState.template:
        return 'TEMPLATE';
    }
  }
}

enum RuntimeReadiness {
  ready,
  pendingCrmFoundation,
  pendingProjectKnowledge,
  deferredCoding;

  static RuntimeReadiness fromString(String val) {
    switch (val.toUpperCase()) {
      case 'READY':
        return RuntimeReadiness.ready;
      case 'PENDING_CRM_FOUNDATION':
        return RuntimeReadiness.pendingCrmFoundation;
      case 'PENDING_PROJECT_KNOWLEDGE':
        return RuntimeReadiness.pendingProjectKnowledge;
      case 'DEFERRED_CODING':
        return RuntimeReadiness.deferredCoding;
      default:
        return RuntimeReadiness.ready;
    }
  }

  String toWireString() {
    switch (this) {
      case RuntimeReadiness.ready:
        return 'READY';
      case RuntimeReadiness.pendingCrmFoundation:
        return 'PENDING_CRM_FOUNDATION';
      case RuntimeReadiness.pendingProjectKnowledge:
        return 'PENDING_PROJECT_KNOWLEDGE';
      case RuntimeReadiness.deferredCoding:
        return 'DEFERRED_CODING';
    }
  }
}

class ProjectStartupTeamMember {
  final String profileKey;
  final String label;
  final TeamDisplayState displayState;
  final RuntimeReadiness runtimeReadiness;
  final String? disabledReason;
  final int? assignmentVersion;
  final DateTime? activatedAt;
  final String? activatedBy;

  const ProjectStartupTeamMember({
    required this.profileKey,
    required this.label,
    required this.displayState,
    required this.runtimeReadiness,
    this.disabledReason,
    this.assignmentVersion,
    this.activatedAt,
    this.activatedBy,
  });

  factory ProjectStartupTeamMember.fromJson(Map<String, dynamic> json) {
    return ProjectStartupTeamMember(
      profileKey: json['profileKey'] as String? ?? '',
      label: json['label'] as String? ?? '',
      displayState: TeamDisplayState.fromString(json['displayState'] as String? ?? ''),
      runtimeReadiness:
          RuntimeReadiness.fromString(json['runtimeReadiness'] as String? ?? ''),
      disabledReason: json['disabledReason'] as String?,
      assignmentVersion: json['assignmentVersion'] as int?,
      activatedAt: json['activatedAt'] != null
          ? DateTime.tryParse(json['activatedAt'] as String)?.toUtc()
          : null,
      activatedBy: json['activatedBy'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'profileKey': profileKey,
      'label': label,
      'displayState': displayState.toWireString(),
      'runtimeReadiness': runtimeReadiness.toWireString(),
      if (disabledReason != null) 'disabledReason': disabledReason,
      if (assignmentVersion != null) 'assignmentVersion': assignmentVersion,
      if (activatedAt != null) 'activatedAt': activatedAt!.toIso8601String(),
      if (activatedBy != null) 'activatedBy': activatedBy,
    };
  }
}
