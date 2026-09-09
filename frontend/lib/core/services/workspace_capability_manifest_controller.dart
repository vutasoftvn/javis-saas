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

  Map<String, CapabilityManifestSurface> get surfaces => Map.unmodifiable(_surfaces);

  Future<void> reload() async {
    isLoading.value = true;
    try {
      final result = await _service.fetch();
      switch (result) {
        case ApiSuccess<WorkspaceCapabilityManifest>(:final data):
          _surfaces
            ..clear()
            ..addEntries(data.surfaces.map((s) => MapEntry(s.surfaceKey, s)));
          version.value = data.version;
          hasLoadedSnapshot.value = true;
          lastError.value = null;
        case ApiFailure<WorkspaceCapabilityManifest>(:final failure):
          _surfaces.clear();
          hasLoadedSnapshot.value = false;
          lastError.value = failure.message;
      }
    } catch (e) {
      debugPrint('[WorkspaceCapabilityManifestController] reload error: $e');
      _surfaces.clear();
      hasLoadedSnapshot.value = false;
      lastError.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }

  void clear() {
    _surfaces.clear();
    hasLoadedSnapshot.value = false;
    version.value = null;
    lastError.value = null;
  }

  /// Trạng thái server-owned cho một surface. Fail closed khi chưa có snapshot
  /// hoặc surface không có trong manifest.
  SurfaceStatus statusFor(String surfaceKey) {
    if (!hasLoadedSnapshot.value) return SurfaceStatus.unavailable;
    return _surfaces[surfaceKey]?.surfaceStatus ?? SurfaceStatus.unavailable;
  }

  CapabilityManifestSurface? surfaceFor(String surfaceKey) => _surfaces[surfaceKey];

  bool isInteractive(String surfaceKey) {
    final s = statusFor(surfaceKey);
    return s == SurfaceStatus.available || s == SurfaceStatus.pilot;
  }
}
