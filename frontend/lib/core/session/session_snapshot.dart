/// Task 4 — trạng thái phiên làm việc đã được XÁC MINH bởi server (không
/// suy diễn từ cache client), commit đúng MỘT lần vào [SessionController]
/// sau khi cả hai bước xác minh (identity + session-context) đều qua.
library;

/// Metadata runtime (mode/presence/heartbeat) đi kèm mỗi session snapshot,
/// lấy trực tiếp từ response server-authoritative của
/// `GET /platform/workspaces/:workspaceId/session-context` (Task 3) — không
/// tự suy diễn lại ở client.
final class SessionRuntimeInfo {
  const SessionRuntimeInfo({
    required this.mode,
    required this.modeSource,
    required this.presenceStatus,
    required this.lastHeartbeatAt,
    required this.asOf,
  });

  /// LOCAL_ONLY | REMOTE_ACCESS | CLOUD_CONTINUITY
  final String mode;

  /// "configured" (đọc từ cấu hình canonical) | "inferred" (heuristic tạm,
  /// có thể sai — xem ghi chú tại `workspace-settings.service.ts` Task 3).
  /// Giữ nguyên field này để consumer không coi một giá trị suy đoán như
  /// đã xác minh.
  final String modeSource;

  /// ONLINE | DEGRADED | OFFLINE
  final String presenceStatus;
  final DateTime? lastHeartbeatAt;

  /// Thời điểm server tính toán snapshot này — dùng cho nhãn "dữ liệu tính
  /// đến …" khi hiển thị read-only view, không giả vờ live.
  final DateTime? asOf;
}

final class SessionSnapshot {
  const SessionSnapshot({
    required this.userId,
    required this.workspaceId,
    required this.role,
    required this.runtime,
    required this.capabilities,
  });

  final String userId;
  final String workspaceId;
  final String role;
  final SessionRuntimeInfo runtime;
  final List<String> capabilities;

  /// Tạo bản sao với `userId` được thay thế — dùng khi SessionController cần
  /// hợp nhất kết quả xác minh identity (chứa `userId` thật) với snapshot
  /// runtime lấy từ `SessionContextService.fetch` (endpoint session-context
  /// hiện KHÔNG trả `userId` — xem `WorkspaceSessionContextView`).
  SessionSnapshot withUserId(String userId) => SessionSnapshot(
        userId: userId,
        workspaceId: workspaceId,
        role: role,
        runtime: runtime,
        capabilities: capabilities,
      );
}
