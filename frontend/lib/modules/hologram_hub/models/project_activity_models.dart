class ProjectActivityEvent {
  final String eventId;
  final String workspaceId;
  final String projectId;
  final int projectSequence;
  final String kind;
  final String phase;
  final String status;
  final String actorKind;
  final String actorId;
  final String correlationId;
  final String sourceType;
  final String sourceId;
  final String sourceVersion;
  final String summary;
  final String classification;
  final DateTime occurredAt;
  final DateTime recordedAt;

  ProjectActivityEvent({
    required this.eventId,
    required this.workspaceId,
    required this.projectId,
    required this.projectSequence,
    required this.kind,
    required this.phase,
    required this.status,
    required this.actorKind,
    required this.actorId,
    required this.correlationId,
    required this.sourceType,
    required this.sourceId,
    required this.sourceVersion,
    required this.summary,
    required this.classification,
    required this.occurredAt,
    required this.recordedAt,
  });

  // Group events by kind category (chat, run, tool, approval, decision, task, risk)
  String get category {
    if (kind.startsWith('chat.')) return 'Chat';
    if (kind.startsWith('run.')) return 'Run';
    if (kind.startsWith('tool.')) return 'Tool';
    if (kind.startsWith('approval.')) return 'Approval';
    if (kind.startsWith('decision.')) return 'Decision';
    if (kind.startsWith('task.')) return 'Task';
    if (kind.startsWith('risk.')) return 'Risk';
    return 'System';
  }

  String get icon {
    switch (category) {
      case 'Chat':
        return 'chat';
      case 'Run':
        return 'play_circle';
      case 'Tool':
        return 'settings';
      case 'Approval':
        return 'check_circle';
      case 'Decision':
        return 'lightbulb';
      case 'Task':
        return 'assignment';
      case 'Risk':
        return 'warning';
      default:
        return 'info';
    }
  }

  // Safe to show in UI without exposing raw tokens or prompts
  String get displaySummary => summary;

  factory ProjectActivityEvent.fromJson(Map<String, dynamic> json) {
    return ProjectActivityEvent(
      eventId: json['event_id'] ?? '',
      workspaceId: json['workspace_id'] ?? '',
      projectId: json['project_id'] ?? '',
      projectSequence: json['project_sequence'] ?? 0,
      kind: json['kind'] ?? '',
      phase: json['phase'] ?? '',
      status: json['status'] ?? '',
      actorKind: json['actor_kind'] ?? '',
      actorId: json['actor_id'] ?? '',
      correlationId: json['correlation_id'] ?? '',
      sourceType: json['source_type'] ?? '',
      sourceId: json['source_id'] ?? '',
      sourceVersion: json['source_version'] ?? '',
      summary: json['summary'] ?? '',
      classification: json['classification'] ?? '',
      occurredAt: DateTime.tryParse(json['occurred_at'] ?? '') ?? DateTime.now(),
      recordedAt: DateTime.tryParse(json['recorded_at'] ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'event_id': eventId,
        'workspace_id': workspaceId,
        'project_id': projectId,
        'project_sequence': projectSequence,
        'kind': kind,
        'phase': phase,
        'status': status,
        'actor_kind': actorKind,
        'actor_id': actorId,
        'correlation_id': correlationId,
        'source_type': sourceType,
        'source_id': sourceId,
        'source_version': sourceVersion,
        'summary': summary,
        'classification': classification,
        'occurred_at': occurredAt.toIso8601String(),
        'recorded_at': recordedAt.toIso8601String(),
      };
}
