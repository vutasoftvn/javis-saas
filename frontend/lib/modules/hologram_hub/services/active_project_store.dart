import '../../../core/services/secure_storage_service.dart';

/// Lưu trữ Project ID đang hoạt động per Workspace, chỉ phục hồi UX.
/// Server vẫn xác minh Project ở mỗi request — local storage không phải
/// authority hay xác thực.
///
/// Key: `active_project_id:<workspace_id>` (ví dụ: `active_project_id:ws_1`)
class ActiveProjectStore {
  static String _keyForWorkspace(String workspaceId) =>
      'active_project_id:$workspaceId';

  /// Đọc Project ID được lưu cho một Workspace.
  /// Trả về null nếu chưa lưu hoặc đã bị xoá.
  static Future<String?> read(String workspaceId) async {
    final key = _keyForWorkspace(workspaceId);
    return SecureStorageService.read(key);
  }

  /// Lưu Project ID cho một Workspace.
  /// Ghi đè giá trị cũ nếu có.
  static Future<void> write(String workspaceId, String projectId) async {
    final key = _keyForWorkspace(workspaceId);
    await SecureStorageService.write(key, projectId);
  }

  /// Xoá Project ID được lưu cho một Workspace.
  /// Safe để gọi khi key chưa tồn tại (không throw).
  static Future<void> delete(String workspaceId) async {
    final key = _keyForWorkspace(workspaceId);
    await SecureStorageService.delete(key);
  }
}
