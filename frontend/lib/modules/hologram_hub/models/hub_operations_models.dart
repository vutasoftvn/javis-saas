// Model cho card vận hành 4 tab ở hub (spec 2026-09-27-hub-operations-workspace-design, đợt 1).
// Giải mã đúng hình dạng thật của các route: `/agent/schedules*` (proxy apps/cosa, snake_case)
// và `/operations/projects/:projectId/agent-capability-grants` (company, camelCase).

DateTime? _parseDate(Object? raw) =>
    raw == null ? null : DateTime.tryParse(raw.toString())?.toUtc();

class HubSchedule {
  const HubSchedule({
    required this.id,
    required this.scheduleKind,
    required this.timezone,
    required this.promptTemplate,
    required this.agentProfile,
    required this.state,
    this.projectId,
    this.hour,
    this.minute,
    this.weekdays = const [],
    this.nextRunAt,
    this.lastRunAt,
  });

  final String id;
  final String scheduleKind;
  final String timezone;
  final String promptTemplate;
  final String agentProfile;
  final String state;
  final String? projectId;
  final int? hour;
  final int? minute;
  final List<int> weekdays;
  final DateTime? nextRunAt;
  final DateTime? lastRunAt;

  bool get isEnabled => state == 'enabled';
  bool get isPaused => state == 'paused';
  bool get isArchived => state == 'archived';

  factory HubSchedule.fromJson(Map<String, dynamic> json) {
    return HubSchedule(
      id: json['id']?.toString() ?? '',
      scheduleKind: json['schedule_kind']?.toString() ?? 'one_time',
      timezone: json['timezone']?.toString() ?? 'Asia/Ho_Chi_Minh',
      promptTemplate: json['prompt_template']?.toString() ?? '',
      agentProfile: json['agent_profile']?.toString() ?? 'operations',
      state: json['state']?.toString() ?? 'enabled',
      projectId: json['project_id']?.toString(),
      hour: (json['hour'] as num?)?.toInt(),
      minute: (json['minute'] as num?)?.toInt(),
      weekdays: (json['weekdays'] as List<dynamic>? ?? [])
          .whereType<num>()
          .map((e) => e.toInt())
          .toList(),
      nextRunAt: _parseDate(json['next_run_at']),
      lastRunAt: _parseDate(json['last_run_at']),
    );
  }
}

class HubScheduleExecution {
  const HubScheduleExecution({
    required this.id,
    required this.state,
    this.scheduledFor,
    this.runId,
    this.conversationId,
    this.error,
  });

  final String id;
  final String state;
  final DateTime? scheduledFor;
  final String? runId;
  final String? conversationId;
  final String? error;

  bool get isFailure =>
      state == 'failed' || state == 'enqueue_failed' || state == 'blocked_reauth';

  factory HubScheduleExecution.fromJson(Map<String, dynamic> json) {
    return HubScheduleExecution(
      id: json['id']?.toString() ?? '',
      state: json['state']?.toString() ?? 'queued',
      scheduledFor: _parseDate(json['scheduled_for']),
      runId: json['run_id']?.toString(),
      conversationId: json['conversation_id']?.toString(),
      error: json['error']?.toString(),
    );
  }
}

class HubAgentGrant {
  const HubAgentGrant({
    required this.grantId,
    required this.profileKey,
    required this.capabilityId,
    required this.labelVi,
    required this.labelEn,
    required this.scope,
    required this.status,
    this.grantedAt,
    this.revokedAt,
  });

  final String grantId;
  final String profileKey;
  final String capabilityId;
  final String labelVi;
  final String labelEn;
  final String scope;
  final String status;
  final DateTime? grantedAt;
  final DateTime? revokedAt;

  bool get isActive => status == 'ACTIVE';
  String label({required bool isEn}) => isEn ? labelEn : labelVi;

  factory HubAgentGrant.fromJson(Map<String, dynamic> json) {
    final label = json['label'] is Map<String, dynamic>
        ? json['label'] as Map<String, dynamic>
        : const <String, dynamic>{};
    return HubAgentGrant(
      grantId: json['grantId']?.toString() ?? '',
      profileKey: json['profileKey']?.toString() ?? '',
      capabilityId: json['capabilityId']?.toString() ?? '',
      labelVi: label['vi']?.toString() ?? 'Quyền khác',
      labelEn: label['en']?.toString() ?? 'Other permission',
      scope: json['scope']?.toString() ?? 'PROJECT',
      status: json['status']?.toString() ?? 'ACTIVE',
      grantedAt: _parseDate(json['grantedAt']),
      revokedAt: _parseDate(json['revokedAt']),
    );
  }
}
