import 'package:get/get.dart';

import '../../../core/network/api_result.dart';
import '../models/onboard_dimension_fields.dart';
import '../models/startup_os_models.dart';
import '../services/startup_os_service.dart';

/// Thông điệp cho từng loại lỗi Startup OS — lỗi luôn hiển thị, không bị đổi
/// thành trạng thái rỗng.
String startupOsFailureMessage(ApiFailureDetail failure) => switch (failure.code) {
      ApiFailureCode.unauthenticated => 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
      ApiFailureCode.forbidden => 'Bạn không có quyền thực hiện thao tác này.',
      ApiFailureCode.notFound => 'Không tìm thấy dữ liệu được yêu cầu.',
      ApiFailureCode.invalidRequest => 'Dữ liệu không hợp lệ: ${failure.message}',
      ApiFailureCode.conflict => 'Không thực hiện được: ${failure.message}',
      ApiFailureCode.unavailable ||
      ApiFailureCode.notConnected =>
        'Máy chủ tạm thời không khả dụng. Dữ liệu cũ vẫn được giữ.',
      _ => 'Không tải được dữ liệu: ${failure.message}',
    };

/// Kết quả gửi wizard onboarding: thành công hay dừng ở chiều nào.
sealed class OnboardSubmitOutcome {
  const OnboardSubmitOutcome();
}

final class OnboardSubmitted extends OnboardSubmitOutcome {
  const OnboardSubmitted(this.snapshotId, this.dimensions);
  final String snapshotId;
  final List<String> dimensions;
}

final class OnboardSubmitFailed extends OnboardSubmitOutcome {
  const OnboardSubmitFailed(this.message, {this.savedDimensions = const [], this.failedDimension});
  final String message;

  /// Chiều đã ghi thành công trước khi lỗi (Company lưu append-only, không rollback).
  final List<String> savedDimensions;
  final String? failedDimension;
}

class StartupOsController extends GetxController {
  StartupOsController({StartupOsService? service}) : _service = service ?? StartupOsService();

  final StartupOsService _service;

  final isLoading = false.obs;
  final goalTree = <GoalNode>[].obs;
  final cadences = <DimensionCadence>[].obs;
  final goalsNeedingReview = <GoalNeedingReview>[].obs;
  final pendingProjects = <PendingProject>[].obs;

  final treeError = Rxn<ApiFailureDetail>();
  final cadenceError = Rxn<ApiFailureDetail>();
  final reviewError = Rxn<ApiFailureDetail>();
  final projectsError = Rxn<ApiFailureDetail>();

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  /// Chiều Fast cần cập nhật trước khi đặt Goal (đến hạn/quá hạn/chưa có).
  List<DimensionCadence> get staleFastDimensions =>
      cadences.where((c) => c.isFast && c.needsUpdate).toList(growable: false);

  /// Flatten cây Goal (theo thứ tự hiển thị) — dùng cho dropdown chọn Goal cha.
  List<GoalNode> get flatGoals {
    final out = <GoalNode>[];
    void walk(List<GoalNode> nodes) {
      for (final node in nodes) {
        out.add(node);
        walk(node.children);
      }
    }

    walk(goalTree);
    return out;
  }

  Future<void> loadAll() async {
    isLoading.value = true;
    try {
      await Future.wait([
        _load(_service.getGoalTree, goalTree, treeError),
        _load(_service.getCadenceStatus, cadences, cadenceError),
        _load(_service.getGoalsNeedingReview, goalsNeedingReview, reviewError),
        _load(_service.listPendingProjects, pendingProjects, projectsError),
      ]);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> _load<T>(
    Future<ApiResult<List<T>>> Function() fetch,
    RxList<T> target,
    Rxn<ApiFailureDetail> error,
  ) async {
    final result = await fetch();
    switch (result) {
      case ApiSuccess(:final data):
        target.assignAll(data);
        error.value = null;
      case ApiFailure(:final failure):
        // Giữ dữ liệu thành công trước đó; lỗi hiển thị riêng.
        error.value = failure;
    }
  }

  /// Tạo Goal; trả về kết quả để View hiện cảnh báo ngữ cảnh do Company trả.
  Future<ApiResult<CreatedGoal>> createGoal({
    required String title,
    required GoalType goalType,
    String? parentId,
    String? description,
    String? startDate,
    String? endDate,
  }) async {
    final result = await _service.createGoal(
      title: title,
      goalType: goalType,
      parentId: parentId,
      description: description,
      startDate: startDate,
      endDate: endDate,
    );
    if (result.isSuccess) await loadAll();
    return result;
  }

  Future<ApiResult<void>> completeGoal(String goalId) async {
    final result = await _service.completeGoal(goalId);
    if (result.isSuccess) await loadAll();
    return result;
  }

  Future<ApiResult<Map<String, dynamic>>> loadCompanyContext() => _service.getCompanyContext();

  /// Ghi các chiều đã điền trong wizard rồi chốt snapshot.
  ///
  /// [payloads] chỉ chứa chiều có dữ liệu (đã qua [buildDimensionPayload]). Dừng ở
  /// chiều lỗi đầu tiên và báo rõ chiều nào đã lưu — Company lưu append-only nên
  /// không giả vờ rollback.
  Future<OnboardSubmitOutcome> submitOnboarding({
    required bool fullSetup,
    required Map<String, Map<String, Object>> payloads,
  }) async {
    if (payloads.isEmpty) {
      return const OnboardSubmitFailed('Chưa có chiều nào được điền.');
    }
    final session = await _service.startSession(
      sessionType: fullSetup ? 'initial' : 'partial_update',
      summary: fullSetup ? 'Thiết lập hồ sơ 7 chiều qua form' : 'Cập nhật nhanh 2 chiều Fast qua form',
    );
    final String sessionId;
    switch (session) {
      case ApiSuccess(:final data):
        sessionId = data;
      case ApiFailure(:final failure):
        return OnboardSubmitFailed(startupOsFailureMessage(failure));
    }

    final saved = <String>[];
    for (final entry in payloads.entries) {
      final result = await _service.updateDimension(
        sessionId: sessionId,
        dimension: entry.key,
        data: entry.value,
      );
      if (result case ApiFailure(:final failure)) {
        await loadAll();
        return OnboardSubmitFailed(
          '${dimensionTitle(entry.key)}: ${startupOsFailureMessage(failure)}',
          savedDimensions: saved,
          failedDimension: entry.key,
        );
      }
      saved.add(entry.key);
    }

    final snapshot = await _service.createSnapshot(
      sessionId: sessionId,
      changedDimensions: saved,
      changeReason: fullSetup ? 'Thiết lập hồ sơ qua form' : 'Cập nhật nhanh qua form',
    );
    await loadAll();
    return switch (snapshot) {
      ApiSuccess(:final data) => OnboardSubmitted(data, saved),
      ApiFailure(:final failure) => OnboardSubmitFailed(
          'Đã lưu các chiều nhưng chưa chốt được snapshot: ${startupOsFailureMessage(failure)}',
          savedDimensions: saved,
        ),
    };
  }

  Future<ApiResult<void>> triageProject({
    required String projectId,
    required TriageAction action,
    String? newGoalId,
    String? newObjectiveTitle,
  }) async {
    final result = await _service.triageProject(
      projectId: projectId,
      action: action,
      newGoalId: newGoalId,
      newObjectiveTitle: newObjectiveTitle,
    );
    if (result.isSuccess) await loadAll();
    return result;
  }
}
