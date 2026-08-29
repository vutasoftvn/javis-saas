class AiComplianceDeployment {
  final String id;
  final String status;
  final String ownerName;
  final String assessmentExpiresAt;
  final String providerStatus;
  final String mode;
  final List<String> allowedCapabilities;

  const AiComplianceDeployment({
    required this.id,
    required this.status,
    required this.ownerName,
    required this.assessmentExpiresAt,
    required this.providerStatus,
    this.mode = 'ADVISORY_ONLY',
    this.allowedCapabilities = const [],
  });

  factory AiComplianceDeployment.fromJson(Map<String, dynamic> json) {
    return AiComplianceDeployment(
      id: json['id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'DRAFT',
      ownerName: json['ownerName']?.toString() ?? json['owner_name']?.toString() ?? 'Founder',
      assessmentExpiresAt: json['assessmentExpiresAt']?.toString() ?? json['assessment_expires_at']?.toString() ?? '',
      providerStatus: json['providerStatus']?.toString() ?? json['provider_status']?.toString() ?? 'ACTIVE',
      mode: json['mode']?.toString() ?? 'ADVISORY_ONLY',
      allowedCapabilities: (json['allowedCapabilities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
    );
  }
}

class AiIncidentSummary {
  final String id;
  final String severity;
  final String status;
  final String summary;
  final String createdAt;

  const AiIncidentSummary({
    required this.id,
    required this.severity,
    required this.status,
    required this.summary,
    required this.createdAt,
  });

  factory AiIncidentSummary.fromJson(Map<String, dynamic> json) {
    return AiIncidentSummary(
      id: json['id']?.toString() ?? '',
      severity: json['severity']?.toString() ?? 'LOW',
      status: json['status']?.toString() ?? 'OPEN',
      summary: json['summary']?.toString() ?? '',
      createdAt: json['createdAt']?.toString() ?? json['created_at']?.toString() ?? '',
    );
  }
}

class AiComplianceCenterData {
  final List<AiComplianceDeployment> deployments;
  final List<AiIncidentSummary> recentIncidents;
  final int activeCount;
  final int incidentCount;

  const AiComplianceCenterData({
    required this.deployments,
    required this.recentIncidents,
    required this.activeCount,
    required this.incidentCount,
  });

  factory AiComplianceCenterData.fromJson(Map<String, dynamic> json) {
    final deps = (json['deployments'] as List<dynamic>?)
            ?.map((e) => AiComplianceDeployment.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];
    final incs = (json['recentIncidents'] as List<dynamic>?)
            ?.map((e) => AiIncidentSummary.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];
    return AiComplianceCenterData(
      deployments: deps,
      recentIncidents: incs,
      activeCount: (json['activeCount'] as num?)?.toInt() ?? deps.where((d) => d.status == 'APPROVED_FOR_USE').length,
      incidentCount: (json['incidentCount'] as num?)?.toInt() ?? incs.length,
    );
  }
}
