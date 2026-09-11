import '../../../core/services/secure_storage_service.dart';
import '../models/project_context_resolution.dart';
export '../models/project_context_resolution.dart';

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

  /// Phân giải Project context một cách xác định:
  /// - Stored hợp lệ -> stored
  /// - Stored nhưng không hợp lệ / không có quyền -> stale, xóa store
  /// - Không có stored -> defaulted (chọn min(createdAt, id)), lưu store
  /// - Danh sách rỗng -> missing
  static Future<ProjectContextResolution> resolve({
    required String workspaceId,
    required List<dynamic> projects,
  }) async {
    if (projects.isEmpty) {
      return const ProjectContextResolution(
        kind: ProjectContextResolutionKind.missing,
      );
    }

    final storedId = await read(workspaceId);
    if (storedId != null) {
      dynamic foundProject;
      for (final p in projects) {
        final id = p is Map ? p['id']?.toString() : (p as dynamic).id?.toString();
        if (id == storedId) {
          foundProject = p;
          break;
        }
      }

      if (foundProject != null) {
        return ProjectContextResolution(
          kind: ProjectContextResolutionKind.stored,
          project: foundProject,
        );
      }

      await delete(workspaceId);
      return const ProjectContextResolution(
        kind: ProjectContextResolutionKind.stale,
      );
    }

    final sorted = List<dynamic>.from(projects);
    sorted.sort((a, b) {
      final aCreatedStr =
          a is Map ? a['createdAt']?.toString() : (a as dynamic).createdAt?.toString();
      final bCreatedStr =
          b is Map ? b['createdAt']?.toString() : (b as dynamic).createdAt?.toString();
      final aDate = aCreatedStr != null ? DateTime.tryParse(aCreatedStr)?.toUtc() : null;
      final bDate = bCreatedStr != null ? DateTime.tryParse(bCreatedStr)?.toUtc() : null;

      if (aDate != null && bDate != null) {
        final cmp = aDate.compareTo(bDate);
        if (cmp != 0) return cmp;
      } else if (aDate != null) {
        return -1;
      } else if (bDate != null) {
        return 1;
      }

      final aId =
          (a is Map ? a['id']?.toString() : (a as dynamic).id?.toString()) ?? '';
      final bId =
          (b is Map ? b['id']?.toString() : (b as dynamic).id?.toString()) ?? '';
      return aId.compareTo(bId);
    });

    final oldest = sorted.first;
    final chosenId =
        oldest is Map ? oldest['id']?.toString() : (oldest as dynamic).id?.toString();
    if (chosenId != null && chosenId.isNotEmpty) {
      await write(workspaceId, chosenId);
    }

    return ProjectContextResolution(
      kind: ProjectContextResolutionKind.defaulted,
      project: oldest,
    );
  }
}
