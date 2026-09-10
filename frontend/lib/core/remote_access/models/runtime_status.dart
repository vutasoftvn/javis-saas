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

  /// Fix-review (2026-09-02, final review I-1) — "configured" (đọc từ cấu
  /// hình canonical) | "inferred" (heuristic tạm, có thể sai) | null (chưa
  /// biết nguồn). Bơm từ `SessionRuntimeInfo.modeSource` (`session_snapshot.
  /// dart`) qua `SessionController._commit` — trước đây field này dừng lại ở
  /// tầng session, không đi tiếp tới đây, khiến banner khẳng định chắc nịch
  /// một giá trị `mode` có thể chỉ là suy đoán chưa xác minh.
  final String? modeSource;

  /// Thời điểm quan sát trạng thái này (dùng cho nhãn "dữ liệu tính đến …").
  final DateTime asOf;

  /// Quyết định route từ `POST /cosa/runtime/route` (nếu có).
  final String? routeTarget;
  final String? routeReason;

  RuntimeStatus({
    required this.mode,
    required this.presence,
    this.lastHeartbeatAt,
    this.modeSource,
    DateTime? asOf,
    this.routeTarget,
    this.routeReason,
  }) : asOf = asOf ?? DateTime.now().toUtc();

  /// `true` khi `modeSource` KHÔNG phải "configured" — tức giá trị [mode]
  /// hiện tại chỉ là suy đoán (hoặc không rõ nguồn), chưa được xác minh bằng
  /// canonical config từ `services/company`.
  bool get isModeInferred => modeSource != 'configured';

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
      modeSource: (j['modeSource'] ?? j['mode_source']) as String?,
      asOf: _dt(j['asOf'] ?? j['as_of']),
      routeTarget: (j['target'] ?? j['routeTarget']) as String?,
      routeReason: (j['reason'] ?? j['routeReason']) as String?,
    );
  }

  RuntimeStatus copyWith({
    RuntimeMode? mode,
    NodePresence? presence,
    DateTime? lastHeartbeatAt,
    String? modeSource,
    DateTime? asOf,
    String? routeTarget,
    String? routeReason,
  }) =>
      RuntimeStatus(
        mode: mode ?? this.mode,
        presence: presence ?? this.presence,
        lastHeartbeatAt: lastHeartbeatAt ?? this.lastHeartbeatAt,
        modeSource: modeSource ?? this.modeSource,
        asOf: asOf ?? this.asOf,
        routeTarget: routeTarget ?? this.routeTarget,
        routeReason: routeReason ?? this.routeReason,
      );

  /// Fix-review (2026-09-02, final review I-3) — trước đây chỉ đặc cách
  /// `remoteAccess`, bỏ sót `CLOUD_CONTINUITY` (cùng đi qua node/relay từ xa
  /// có thể offline độc lập — xem `MutationGate._checkRelayedMutation`, dùng
  /// CHUNG một quy tắc cho cả hai mode) — một workspace CLOUD_CONTINUITY +
  /// OFFLINE bị `MutationGate` chặn (`blockedOffline`) nhưng KHÔNG có banner
  /// giải thích lý do, tạo ra dead UI. Mode không nhận diện được (`unknown`)
  /// cũng fail-closed sang chỉ đọc, khớp nhánh fail-closed của
  /// `MutationGate._checkRead`/`_checkMutation` (mặc định `blocked*`, không
  /// bao giờ "allowed").
  bool get _isRelayedMode =>
      mode == RuntimeMode.remoteAccess || mode == RuntimeMode.cloudContinuity;

  bool get isReadOnly =>
      (_isRelayedMode && presence != NodePresence.online) ||
      mode == RuntimeMode.unknown;

  bool get isOffline =>
      (_isRelayedMode && presence == NodePresence.offline) ||
      mode == RuntimeMode.unknown;

  bool get isDegraded => presence == NodePresence.degraded;

  /// Có cần hiện banner cảnh báo không (ẩn khi local-only / online bình thường).
  bool get needsBanner =>
      isOffline || isDegraded || (_isRelayedMode && isReadOnly);

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

  /// Fix-review (2026-09-02, final review I-1) — hậu tố hedge khi [mode] hiện
  /// tại chỉ là suy đoán ([isModeInferred]), chưa được xác minh bằng canonical
  /// config — không để banner khẳng định chắc nịch một giá trị có thể sai.
  /// Cùng tông với comment `runtimeModeSource` ở Task 3
  /// (`workspace-settings.service.ts`): "suy đoán", không phải sự thật đã xác
  /// nhận.
  String get _inferredHedgeSuffix =>
      isModeInferred ? ' (chế độ runtime hiện tại là suy đoán, chưa xác minh)' : '';

  String get bannerMessage {
    // Fix-review (2026-09-02, final review I-3) — mode không nhận diện được
    // (mới trong tương lai, hoặc lỗi parse) fail-closed sang read-only qua
    // `isOffline`/`isReadOnly` ở trên nhưng cần thông điệp riêng, không mượn
    // nhầm câu "node offline" (sai nguyên nhân, gây hiểu lầm là do mất kết
    // nối trong khi thực ra là do giá trị mode lạ).
    if (mode == RuntimeMode.unknown) {
      return 'Không xác định được chế độ runtime của workspace — tạm khoá thao tác, chỉ đọc để an toàn.';
    }
    if (isOffline) {
      return 'Workspace runtime node đang offline — chỉ đọc, không chạy tác vụ. '
          'Không tự chuyển sang cloud.$_inferredHedgeSuffix';
    }
    if (isDegraded) {
      return 'Kết nối tới runtime node chập chờn — thao tác có thể chậm hoặc lỗi.$_inferredHedgeSuffix';
    }
    if (isReadOnly) {
      return 'Đang ở chế độ chỉ đọc.$_inferredHedgeSuffix';
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
