class MissionEvent {
  final String eventId;
  final String runId;
  final String agentKey;
  final String eventType;
  final String timestamp;
  final Map<String, dynamic> data;

  MissionEvent({
    required this.eventId,
    required this.runId,
    required this.agentKey,
    required this.eventType,
    required this.timestamp,
    required this.data,
  });

  factory MissionEvent.fromJson(Map<String, dynamic> json) {
    return MissionEvent(
      eventId: (json['event_id'] ?? '').toString(),
      runId: (json['run_id'] ?? '').toString(),
      agentKey: (json['agent_key'] ?? 'chief_of_staff').toString(),
      eventType: (json['event_type'] ?? '').toString(),
      timestamp: (json['timestamp'] ?? '').toString(),
      data: json['data'] is Map<String, dynamic> ? json['data'] as Map<String, dynamic> : {},
    );
  }
}

class ChiefOfStaffMission {
  final String missionId;
  final String workspaceId;
  final String goal;
  final String diagnosis;
  final Map<String, dynamic> specialistReports;
  final List<String> priorities;
  final List<dynamic> actionPlan;
  final List<dynamic> requiredApprovals;
  final String status;

  ChiefOfStaffMission({
    required this.missionId,
    required this.workspaceId,
    required this.goal,
    required this.diagnosis,
    required this.specialistReports,
    required this.priorities,
    required this.actionPlan,
    required this.requiredApprovals,
    required this.status,
  });

  factory ChiefOfStaffMission.fromJson(Map<String, dynamic> json) {
    return ChiefOfStaffMission(
      missionId: (json['mission_id'] ?? '').toString(),
      workspaceId: (json['workspace_id'] ?? '').toString(),
      goal: (json['goal'] ?? '').toString(),
      diagnosis: (json['diagnosis'] ?? '').toString(),
      specialistReports: json['specialist_reports'] is Map<String, dynamic>
          ? json['specialist_reports'] as Map<String, dynamic>
          : {},
      priorities: (json['priorities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      actionPlan: json['action_plan'] is List ? json['action_plan'] as List<dynamic> : [],
      requiredApprovals: json['required_approvals'] is List ? json['required_approvals'] as List<dynamic> : [],
      status: (json['status'] ?? 'completed').toString(),
    );
  }
}
