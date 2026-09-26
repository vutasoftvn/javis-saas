// Task 7 (PHẠM VI MỞ RỘNG 2026-09-14) — controller GetX tối thiểu để mở route
// strategy thật. Controller KHÔNG có BuildContext nên không tự mở dialog
// (showOkrWeeklyGeneratorDialog) — chỉ trả Future<void>/throw khi lỗi, View
// (strategy_view.dart) mới là nơi gọi dialog sau khi publish() thành công.
//
// Đợt 4 (plan 2026-09-26-dashboard-full-management) — thêm tạo/xoá Objective
// và Key Result để màn "Chưa có Objective nào" có hành động thật.
import 'package:get/get.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../hologram_hub/services/active_project_store.dart';
import '../models/mvp_strategy_models.dart';
import '../services/okr_service.dart';

class StrategyController extends GetxController {
  StrategyController({OkrService? okrService, Future<String?> Function()? activeProjectResolver})
      : _okrService = okrService ?? OkrService(),
        _activeProjectResolver = activeProjectResolver ?? _readActiveProject;

  final OkrService _okrService;
  final Future<String?> Function() _activeProjectResolver;

  final isLoading = false.obs;
  final objectives = <MvpObjective>[].obs;

  /// Key Result theo objectiveId — backend `GET /operations/key-results` trả
  /// toàn bộ KR của workspace, nhóm ở client.
  final keyResultsByObjective = <String, List<Map<String, dynamic>>>{}.obs;
  final errorMessage = RxnString();

  static Future<String?> _readActiveProject() async {
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId == null || workspaceId.isEmpty) return null;
    return ActiveProjectStore.read(workspaceId);
  }

  @override
  void onInit() {
    super.onInit();
    loadObjectives();
  }

  Future<void> loadObjectives() async {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      final result = await _okrService.getObjectives();
      if (result.isFailure) {
        errorMessage.value = result.errorMessage;
        return;
      }
      objectives.value = result.items.map(MvpObjective.fromJson).toList();
      final krResult = await _okrService.getKeyResults();
      final grouped = <String, List<Map<String, dynamic>>>{};
      for (final kr in krResult.items) {
        final objectiveId = kr['objectiveId']?.toString() ?? kr['objective_id']?.toString();
        if (objectiveId == null) continue;
        grouped.putIfAbsent(objectiveId, () => []).add(kr);
      }
      keyResultsByObjective.assignAll(grouped);
    } finally {
      isLoading.value = false;
    }
  }

  /// Publish 1 Objective rồi refresh danh sách. Ném lỗi ra ngoài nếu thất
  /// bại — View xử lý hiển thị (snackbar/toast), controller không biết UI.
  Future<void> publish(String objectiveId) async {
    await _okrService.publishObjective(objectiveId);
    await loadObjectives();
  }

  /// Tạo Objective cho Project đang chọn. Không có Project → ném lỗi rõ ràng
  /// thay vì để backend tự gán "project đầu tiên" (CLAUDE.md quy tắc 14).
  Future<void> createObjective({required String title, String? why}) async {
    final projectId = await _activeProjectResolver();
    if (projectId == null || projectId.isEmpty) {
      throw StateError('Chưa chọn Project — hãy chọn Project ở Hub trước khi tạo Objective.');
    }
    await _okrService.createObjective(
      title: title,
      projectId: projectId,
      why: (why == null || why.trim().isEmpty) ? null : why.trim(),
    );
    await loadObjectives();
  }

  Future<void> deleteObjective(String objectiveId) async {
    await _okrService.deleteObjective(objectiveId);
    await loadObjectives();
  }

  Future<void> addKeyResult({
    required String objectiveId,
    required String title,
    required double targetValue,
    double? baselineValue,
    String? unit,
  }) async {
    await _okrService.createKeyResult(
      objectiveId: objectiveId,
      title: title,
      targetValue: targetValue,
      baselineValue: baselineValue,
      unit: (unit == null || unit.trim().isEmpty) ? null : unit.trim(),
    );
    await loadObjectives();
  }

  Future<void> checkinKeyResult(String keyResultId, double value) async {
    await _okrService.checkinKeyResult(keyResultId, value);
    await loadObjectives();
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    await _okrService.deleteKeyResult(keyResultId);
    await loadObjectives();
  }
}
