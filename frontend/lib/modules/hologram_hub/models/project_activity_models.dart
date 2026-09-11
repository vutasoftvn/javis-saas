/// Mô hình durable project activity event từ API projection
class ProjectActivityEvent {
  final String eventId;
  final String workspaceId;
  final String projectId;
  final int projectSequence;
  final String kind; // run.queued, run.completed, tool.requested, etc.
  final String? phase; // pending, in_progress, completed, failed
  final String? status;
  final String? actorId;
  final String? actorKind; // ai, human, system
  final String? correlationId;
  final String? sourceType; // run, message, tool, approval, task, decision
  final String? sourceId;
  final String? sourceVersion;
  final String? summary; // redacted, safe for UI
  final String? classification; // internal, restricted, public
  final String? integrityHash;
  final DateTime? occurredAt;
  final DateTime? recordedAt;

  ProjectActivityEvent({
    required this.eventId,
    required this.workspaceId,
    required this.projectId,
    required this.projectSequence,
    required this.kind,
    this.phase,
    this.status,
    this.actorId,
    this.actorKind,
    this.correlationId,
    this.sourceType,
    this.sourceId,
    this.sourceVersion,
    this.summary,
    this.classification,
    this.integrityHash,
    this.occurredAt,
    this.recordedAt,
  });

  /// Group events by kind category (chat, run, tool, approval, decision, task, risk)
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

  /// Safe to show in UI without exposing raw tokens or prompts
  String get displaySummary => summary ?? '(no summary)';

  factory ProjectActivityEvent.fromJson(Map<String, dynamic> json) {
    return ProjectActivityEvent(
      eventId: json['event_id']?.toString() ?? '',
      workspaceId: json['workspace_id']?.toString() ?? '',
      projectId: json['project_id']?.toString() ?? '',
      projectSequence: (json['project_sequence'] is num)
          ? (json['project_sequence'] as num).toInt()
          : 0,
      kind: json['kind']?.toString() ?? 'unknown',
      phase: json['phase']?.toString(),
      status: json['status']?.toString(),
      actorId: json['actor_id']?.toString(),
      actorKind: json['actor_kind']?.toString(),
      correlationId: json['correlation_id']?.toString(),
      sourceType: json['source_type']?.toString(),
      sourceId: json['source_id']?.toString(),
      sourceVersion: json['source_version']?.toString(),
      summary: json['summary']?.toString(),
      classification: json['classification']?.toString(),
      integrityHash: json['integrity_hash']?.toString(),
      occurredAt: json['occurred_at'] != null
          ? DateTime.tryParse(json['occurred_at'].toString())
          : null,
      recordedAt: json['recorded_at'] != null
          ? DateTime.tryParse(json['recorded_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'event_id': eventId,
        'workspace_id': workspaceId,
        'project_id': projectId,
        'project_sequence': projectSequence,
        'kind': kind,
        if (phase != null) 'phase': phase,
        if (status != null) 'status': status,
        if (actorId != null) 'actor_id': actorId,
        if (actorKind != null) 'actor_kind': actorKind,
        if (correlationId != null) 'correlation_id': correlationId,
        if (sourceType != null) 'source_type': sourceType,
        if (sourceId != null) 'source_id': sourceId,
        if (sourceVersion != null) 'source_version': sourceVersion,
        if (summary != null) 'summary': summary,
        if (classification != null) 'classification': classification,
        if (integrityHash != null) 'integrity_hash': integrityHash,
        if (occurredAt != null) 'occurred_at': occurredAt?.toIso8601String(),
        if (recordedAt != null) 'recorded_at': recordedAt?.toIso8601String(),
      };
}

/// Response từ activity list endpoint
class ProjectActivityListResponse {
  final List<ProjectActivityEvent> items;
  final int total;

  ProjectActivityListResponse({
    required this.items,
    required this.total,
  });

  factory ProjectActivityListResponse.fromJson(Map<String, dynamic> json) {
    return ProjectActivityListResponse(
      items: (json['items'] as List<dynamic>?)
              ?.map((item) =>
                  ProjectActivityEvent.fromJson(item as Map<String, dynamic>))
              .toList() ??
          [],
      total: (json['total'] is num) ? (json['total'] as num).toInt() : 0,
    );
  }
}
