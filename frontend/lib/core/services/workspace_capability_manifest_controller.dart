import 'package:flutter/foundation.dart';
import 'package:get/get.dart';

import '../network/api_result.dart';
import 'workspace_capability_manifest_model.dart';
import 'workspace_capability_manifest_service.dart';

/// Giữ snapshot manifest per-workspace và trả `surfaceStatus` server-owned.
///
/// FAIL CLOSED: trước khi có snapshot, hoặc khi request lỗi, mọi surface là
/// [SurfaceStatus.unavailable]. Client không được "đoán" một surface là live.
class WorkspaceCapabilityManifestController extends GetxController {
  WorkspaceCapabilityManifestController({WorkspaceCapabilityManifestApi? service})
      : _service = service ?? WorkspaceCapabilityManifestService();

  final WorkspaceCapabilityManifestApi _service;

  final RxMap<String, CapabilityManifestSurface> _surfaces =
      <String, CapabilityManifestSurface>{}.obs;
  final RxBool isLoading = false.obs;
  final RxBool hasLoadedSnapshot = false.obs;
  final RxnString lastError = RxnString();
  final RxnString version = RxnString();

  /// Workspace mà manifest hiện tại PHẢI thuộc về. Một response có
  /// `workspaceId` khác giá trị này bị bỏ qua (stale khi đang switch).
  final RxnString _currentWorkspaceId = RxnString();
  String? get currentWorkspaceId => _currentWorkspaceId.value;
  final RxnString _loadedWorkspaceId = RxnString();

  Map<String, CapabilityManifestSurface> get surfaces => Map.unmodifiable(_surfaces);

  /// Bắt đầu chuyển workspace: đặt workspace mục tiêu và XOÁ snapshot cũ ngay
  /// lập tức để không surface nào của workspace trước còn được render trong lúc
  /// chờ response mới.
  void beginWorkspaceSwitch(String workspaceId) {
    _currentWorkspaceId.value = workspaceId;
    _surfaces.clear();
    _loadedWorkspaceId.value = null;
    hasLoadedSnapshot.value = false;
    lastError.value = null;
    version.value = null;
  }

  /// Nạp manifest cho một workspace cụ thể. Chỉ chấp nhận response khi
  /// `data.workspaceId` khớp workspace mục tiêu hiện tại.
  Future<void> reloadForWorkspace(String workspaceId) async {
    _currentWorkspaceId.value = workspaceId;
    await _reload(expectedWorkspaceId: workspaceId);
  }

  /// Back-compat: nạp cho workspace mục tiêu hiện tại (nếu có).
  Future<void> reload() => _reload(expectedWorkspaceId: _currentWorkspaceId.value);

  Future<void> _reload({String? expectedWorkspaceId}) async {
    isLoading.value = true;
    try {
      final result = await _service.fetch();
      switch (result) {
        case ApiSuccess<WorkspaceCapabilityManifest>(:final data):
          // Bỏ qua response cho workspace không phải mục tiêu hiện tại.
          if (expectedWorkspaceId != null &&
              data.workspaceId != expectedWorkspaceId) {
            debugPrint(
              '[WorkspaceCapabilityManifestController] ignoring stale manifest '
              'for ${data.workspaceId}, expected $expectedWorkspaceId',
            );
            _surfaces.clear();
            _loadedWorkspaceId.value = null;
            hasLoadedSnapshot.value = false;
            return;
          }
          _surfaces
            ..clear()
            ..addEntries(data.surfaces.map((s) => MapEntry(s.surfaceKey, s)));
          version.value = data.version;
          _loadedWorkspaceId.value = data.workspaceId;
          hasLoadedSnapshot.value = true;
          lastError.value = null;
        case ApiFailure<WorkspaceCapabilityManifest>(:final failure):
          _surfaces.clear();
          _loadedWorkspaceId.value = null;
          hasLoadedSnapshot.value = false;
          lastError.value = failure.message;
      }
    } catch (e) {
      debugPrint('[WorkspaceCapabilityManifestController] reload error: $e');
      _surfaces.clear();
      _loadedWorkspaceId.value = null;
      hasLoadedSnapshot.value = false;
      lastError.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }

  void clear() {
    _surfaces.clear();
    _loadedWorkspaceId.value = null;
    _currentWorkspaceId.value = null;
    hasLoadedSnapshot.value = false;
    version.value = null;
    lastError.value = null;
  }

  /// Trạng thái server-owned cho một surface. Fail closed khi chưa có snapshot,
  /// khi surface không có trong manifest, HOẶC khi snapshot đã nạp thuộc về một
  /// workspace khác workspace mục tiêu hiện tại.
  SurfaceStatus statusFor(String surfaceKey) {
    if (!hasLoadedSnapshot.value) return SurfaceStatus.unavailable;
    if (_currentWorkspaceId.value != null &&
        _loadedWorkspaceId.value != _currentWorkspaceId.value) {
      return SurfaceStatus.unavailable;
    }
    return _surfaces[surfaceKey]?.surfaceStatus ?? SurfaceStatus.unavailable;
  }

  CapabilityManifestSurface? surfaceFor(String surfaceKey) => _surfaces[surfaceKey];

  bool isInteractive(String surfaceKey) {
    final s = statusFor(surfaceKey);
    return s == SurfaceStatus.available || s == SurfaceStatus.pilot;
  }
}
