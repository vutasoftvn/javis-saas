/// M5 §5/§6 — trạng thái runtime của workspace hiện tại, dùng để quyết định
/// UI read-only / offline và target routing của [ApiClient].
///
/// `REMOTE_ACCESS` + node KHÔNG `ONLINE` ⇒ UI chỉ đọc, KHÔNG âm thầm chạy cloud
/// (guardrail 7). Read-only view phải hiện `as_of` timestamp, không giả vờ live.
library;

enum RuntimeMode { localOnly, remoteAccess, cloudContinuity, unknown }

enum NodePresence { online, degraded, offline, unknown }

class RuntimeStatus {
  final RuntimeMode mode;
  final NodePresence presence;
  final DateTime? lastHeartbeatAt;

  /// Thời điểm quan sát trạng thái này (dùng cho nhãn "dữ liệu tính đến …").
  final DateTime asOf;

  /// Quyết định route từ `POST /cosa/runtime/route` (nếu có).
  final String? routeTarget;
  final String? routeReason;

  RuntimeStatus({
    required this.mode,
    required this.presence,
    this.lastHeartbeatAt,
    DateTime? asOf,
    this.routeTarget,
    this.routeReason,
  }) : asOf = asOf ?? DateTime.now().toUtc();

  static RuntimeMode parseMode(String? s) {
    switch (s) {
      case 'LOCAL_ONLY':
        return RuntimeMode.localOnly;
      case 'REMOTE_ACCESS':
        return RuntimeMode.remoteAccess;
      case 'CLOUD_CONTINUITY':
        return RuntimeMode.cloudContinuity;
      default:
        return RuntimeMode.unknown;
    }
  }

  static NodePresence parsePresence(String? s) {
    switch (s) {
      case 'ONLINE':
        return NodePresence.online;
      case 'DEGRADED':
        return NodePresence.degraded;
      case 'OFFLINE':
        return NodePresence.offline;
      default:
        return NodePresence.unknown;
    }
  }

  static String modeWire(RuntimeMode m) {
    switch (m) {
      case RuntimeMode.localOnly:
        return 'LOCAL_ONLY';
      case RuntimeMode.remoteAccess:
        return 'REMOTE_ACCESS';
      case RuntimeMode.cloudContinuity:
        return 'CLOUD_CONTINUITY';
      case RuntimeMode.unknown:
        return 'UNKNOWN';
    }
  }

  static String presenceWire(NodePresence p) {
    switch (p) {
      case NodePresence.online:
        return 'ONLINE';
      case NodePresence.degraded:
        return 'DEGRADED';
      case NodePresence.offline:
        return 'OFFLINE';
      case NodePresence.unknown:
        return 'UNKNOWN';
    }
  }

  static DateTime? _dt(dynamic v) {
    if (v is String && v.isNotEmpty) return DateTime.tryParse(v)?.toUtc();
    return null;
  }

  /// Chấp nhận cả camelCase (Encore) lẫn snake_case (control-plane / router).
  factory RuntimeStatus.fromJson(Map<String, dynamic> j) {
    final node = (j['node'] is Map) ? j['node'] as Map<String, dynamic> : j;
    return RuntimeStatus(
      mode: parseMode((j['runtimeMode'] ?? j['runtime_mode']) as String?),
      presence: parsePresence(
        (j['presence'] ??
                j['presence_status'] ??
                node['presence'] ??
                node['presenceStatus'] ??
                node['presence_status'])
            as String?,
      ),
      lastHeartbeatAt: _dt(
        j['lastHeartbeatAt'] ??
            j['last_heartbeat_at'] ??
            node['lastHeartbeatAt'] ??
            node['last_heartbeat_at'],
      ),
      asOf: _dt(j['asOf'] ?? j['as_of']),
      routeTarget: (j['target'] ?? j['routeTarget']) as String?,
      routeReason: (j['reason'] ?? j['routeReason']) as String?,
    );
  }

  RuntimeStatus copyWith({
    RuntimeMode? mode,
    NodePresence? presence,
    DateTime? lastHeartbeatAt,
    DateTime? asOf,
    String? routeTarget,
    String? routeReason,
  }) =>
      RuntimeStatus(
        mode: mode ?? this.mode,
        presence: presence ?? this.presence,
        lastHeartbeatAt: lastHeartbeatAt ?? this.lastHeartbeatAt,
        asOf: asOf ?? this.asOf,
        routeTarget: routeTarget ?? this.routeTarget,
        routeReason: routeReason ?? this.routeReason,
      );

  /// REMOTE_ACCESS + node không ONLINE ⇒ chỉ đọc.
  bool get isReadOnly =>
      mode == RuntimeMode.remoteAccess && presence != NodePresence.online;

  bool get isOffline =>
      mode == RuntimeMode.remoteAccess && presence == NodePresence.offline;

  bool get isDegraded => presence == NodePresence.degraded;

  /// Có cần hiện banner cảnh báo không (ẩn khi local-only / online bình thường).
  bool get needsBanner =>
      isOffline || isDegraded || (mode == RuntimeMode.remoteAccess && isReadOnly);

  String get presenceLabel {
    switch (presence) {
      case NodePresence.online:
        return 'Trực tuyến';
      case NodePresence.degraded:
        return 'Kết nối chập chờn';
      case NodePresence.offline:
        return 'Node offline';
      case NodePresence.unknown:
        return 'Không rõ trạng thái';
    }
  }

  String get bannerMessage {
    if (isOffline) {
      return 'Workspace runtime node đang offline — chỉ đọc, không chạy tác vụ. Không tự chuyển sang cloud.';
    }
    if (isDegraded) {
      return 'Kết nối tới runtime node chập chờn — thao tác có thể chậm hoặc lỗi.';
    }
    if (isReadOnly) {
      return 'Đang ở chế độ chỉ đọc.';
    }
    return '';
  }

  /// Nhãn "as_of" cho read-only stale view.
  String? get stalenessLabel {
    if (!isReadOnly) return null;
    return 'Dữ liệu tính đến ${_fmtLocal(asOf)}';
  }

  static String _fmtLocal(DateTime utc) {
    final d = utc.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.hour)}:${two(d.minute)} ${two(d.day)}/${two(d.month)}';
  }
}
