/// Client model cho `WorkspaceCapabilityManifest` (Founder Trial R1 — spec §7.1).
///
/// Server là authority của `surfaceStatus`. Client KHÔNG suy luận từ route,
/// role cache hay dữ liệu rỗng — chỉ đọc đúng những gì manifest nói.
library;

enum SurfaceStatus {
  available,
  pilot,
  planned,
  configurationRequired,
  unavailable;

  static SurfaceStatus fromWire(String? raw) {
    switch ((raw ?? '').toUpperCase().trim()) {
      case 'AVAILABLE':
        return SurfaceStatus.available;
      case 'PILOT':
        return SurfaceStatus.pilot;
      case 'PLANNED':
        return SurfaceStatus.planned;
      case 'CONFIGURATION_REQUIRED':
        return SurfaceStatus.configurationRequired;
      case 'UNAVAILABLE':
        return SurfaceStatus.unavailable;
      default:
        // Giá trị lạ = fail closed.
        return SurfaceStatus.unavailable;
    }
  }
}

class CapabilityManifestSurface {
  const CapabilityManifestSurface({
    required this.surfaceKey,
    required this.moduleKey,
    required this.featureKey,
    required this.surfaceStatus,
    required this.requiredCapabilities,
    required this.requiredConnectorKeys,
    required this.entitled,
    required this.reasons,
    required this.contractEndpoint,
    required this.releaseNote,
    required this.updatedAt,
  });

  final String surfaceKey;
  final String moduleKey;
  final String featureKey;
  final SurfaceStatus surfaceStatus;
  final List<String> requiredCapabilities;
  final List<String> requiredConnectorKeys;
  final bool entitled;
  final List<String> reasons;
  final String? contractEndpoint;
  final String? releaseNote;
  final String? updatedAt;

  factory CapabilityManifestSurface.fromJson(Map<String, dynamic> json) {
    List<String> strList(dynamic v) =>
        (v as List?)?.map((e) => e.toString()).toList() ?? const [];
    return CapabilityManifestSurface(
      surfaceKey: json['surfaceKey']?.toString() ?? '',
      moduleKey: json['moduleKey']?.toString() ?? '',
      featureKey: json['featureKey']?.toString() ?? '',
      surfaceStatus: SurfaceStatus.fromWire(json['surfaceStatus']?.toString()),
      requiredCapabilities: strList(json['requiredCapabilities']),
      requiredConnectorKeys: strList(json['requiredConnectorKeys']),
      entitled: json['entitled'] == true,
      reasons: strList(json['reasons']),
      contractEndpoint: json['contractEndpoint']?.toString(),
      releaseNote: json['releaseNote']?.toString(),
      updatedAt: json['updatedAt']?.toString(),
    );
  }
}

class WorkspaceCapabilityManifest {
  const WorkspaceCapabilityManifest({
    required this.version,
    required this.workspaceId,
    required this.surfaces,
  });

  final String version;
  final String workspaceId;
  final List<CapabilityManifestSurface> surfaces;

  factory WorkspaceCapabilityManifest.fromJson(Map<String, dynamic> json) {
    return WorkspaceCapabilityManifest(
      version: json['version']?.toString() ?? '',
      workspaceId: (json['organizationId'] ?? json['workspaceId'])?.toString() ?? '',
      surfaces: (json['surfaces'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(CapabilityManifestSurface.fromJson)
              .toList() ??
          const [],
    );
  }
}
