class OkrCycleDto {
  final String id;
  final String workspaceId;
  final String name;
  final String status;
  final String? createdAt;

  const OkrCycleDto({
    required this.id,
    required this.workspaceId,
    required this.name,
    this.status = 'active',
    this.createdAt,
  });

  factory OkrCycleDto.fromJson(Map<String, dynamic> json) {
    return OkrCycleDto(
      id: (json['id'] ?? '').toString(),
      workspaceId: (json['workspace_id'] ?? json['workspaceId'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      status: (json['status'] ?? 'active').toString(),
      createdAt: json['created_at']?.toString() ?? json['createdAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'name': name,
      'status': status,
      if (createdAt != null) 'createdAt': createdAt,
    };
  }
}

class ObjectiveDto {
  final String id;
  final String workspaceId;
  final String cycleId;
  final String title;
  final String? why;
  final String? ownerMemberId;
  final String status;
  final List<String> projectIds;
  final String? createdAt;

  const ObjectiveDto({
    required this.id,
    required this.workspaceId,
    required this.cycleId,
    required this.title,
    this.why,
    this.ownerMemberId,
    this.status = 'active',
    this.projectIds = const [],
    this.createdAt,
  });

  factory ObjectiveDto.fromJson(Map<String, dynamic> json) {
    return ObjectiveDto(
      id: (json['id'] ?? '').toString(),
      workspaceId: (json['workspace_id'] ?? json['workspaceId'] ?? '').toString(),
      cycleId: (json['cycle_id'] ?? json['cycleId'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      why: json['why']?.toString(),
      ownerMemberId: (json['owner_member_id'] ?? json['ownerMemberId'])?.toString(),
      status: (json['status'] ?? 'active').toString(),
      projectIds: (json['project_ids'] ?? json['projectIds'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      createdAt: json['created_at']?.toString() ?? json['createdAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'workspaceId': workspaceId,
      'cycleId': cycleId,
      'title': title,
      if (why != null) 'why': why,
      if (ownerMemberId != null) 'ownerMemberId': ownerMemberId,
      'status': status,
      'projectIds': projectIds,
      if (createdAt != null) 'createdAt': createdAt,
    };
  }
}

class KeyResultDto {
  final String id;
  final String objectiveId;
  final String title;
  final double targetValue;
  final double currentValue;
  final String unit;
  final String status;
  final String? createdAt;

  const KeyResultDto({
    required this.id,
    required this.objectiveId,
    required this.title,
    this.targetValue = 100.0,
    this.currentValue = 0.0,
    this.unit = '%',
    this.status = 'active',
    this.createdAt,
  });

  double get progressPercentage {
    if (targetValue <= 0) return 0.0;
    return (currentValue / targetValue).clamp(0.0, 1.0);
  }

  factory KeyResultDto.fromJson(Map<String, dynamic> json) {
    return KeyResultDto(
      id: (json['id'] ?? '').toString(),
      objectiveId: (json['objective_id'] ?? json['objectiveId'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      targetValue: double.tryParse((json['target_value'] ?? json['targetValue'] ?? 100).toString()) ?? 100.0,
      currentValue: double.tryParse((json['current_value'] ?? json['currentValue'] ?? 0).toString()) ?? 0.0,
      unit: (json['unit'] ?? '%').toString(),
      status: (json['status'] ?? 'active').toString(),
      createdAt: json['created_at']?.toString() ?? json['createdAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'objectiveId': objectiveId,
      'title': title,
      'targetValue': targetValue,
      'currentValue': currentValue,
      'unit': unit,
      'status': status,
      if (createdAt != null) 'createdAt': createdAt,
    };
  }
}
