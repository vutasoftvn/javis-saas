import 'package:get/get.dart';
import '../models/executive_advisory_board.dart';
import '../services/executive_advisory_board_service.dart';

class ExecutiveAdvisoryBoardController extends GetxController {
  final ExecutiveAdvisoryBoardService _service;

  final RxList<ExecutiveAdvisorRole> roles = <ExecutiveAdvisorRole>[].obs;
  final Rxn<ExecutiveDeliberation> currentDeliberation = Rxn<ExecutiveDeliberation>();
  final RxBool isLoading = false.obs;
  final RxBool isMutating = false.obs;
  final RxnString errorMessage = RxnString();
  final RxnString selectedPreset = RxnString();

  String? currentProjectId;

  ExecutiveAdvisoryBoardController({ExecutiveAdvisoryBoardService? service})
      : _service = service ?? ExecutiveAdvisoryBoardService();

  /// Tải danh sách roles của hội đồng cố vấn theo Project.
  Future<void> loadBoard(String projectId) async {
    currentProjectId = projectId;
    isLoading.value = true;
    errorMessage.value = null;

    final result = await _service.fetchRoles(projectId);
    isLoading.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      roles.assignAll(result.dataOrNull!);
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể tải danh sách ban cố vấn';
    }
  }

  /// Chọn preset Startup Core (startup-discovery hoặc startup-build-launch).
  Future<bool> selectStartupPreset(String projectId, String presetKey) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.selectPreset(
      projectId: projectId,
      presetKey: presetKey,
    );
    isMutating.value = false;

    if (result.isSuccess) {
      selectedPreset.value = presetKey;
      await loadBoard(projectId);
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể chọn preset';
      return false;
    }
  }

  /// Kích hoạt vai trò cố vấn (Founder-only). Cập nhật theo kết quả trả về từ server, không optimistic.
  Future<bool> activateRole({
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.activateRole(
      projectId: projectId,
      roleKey: roleKey,
      expectedVersion: expectedVersion,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      final updated = result.dataOrNull!;
      final idx = roles.indexWhere((r) => r.roleKey == roleKey);
      if (idx >= 0) {
        roles[idx] = updated;
      }
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể kích hoạt vai trò';
      return false;
    }
  }

  /// Tạm dừng / vô hiệu hoá vai trò cố vấn.
  Future<bool> disableRole({
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.disableRole(
      projectId: projectId,
      roleKey: roleKey,
      expectedVersion: expectedVersion,
      reason: reason,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      final updated = result.dataOrNull!;
      final idx = roles.indexWhere((r) => r.roleKey == roleKey);
      if (idx >= 0) {
        roles[idx] = updated;
      }
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể tạm dừng vai trò';
      return false;
    }
  }

  /// Tạo bản nháp Deliberation mới.
  Future<ExecutiveDeliberation?> createDraft({
    required String projectId,
    required String title,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.createDraft(
      projectId: projectId,
      title: title,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return result.dataOrNull;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể tạo bản nháp nghị sự';
      return null;
    }
  }

  /// Đóng khung Deliberation.
  Future<bool> frameDeliberation({
    required String projectId,
    required String deliberationId,
    required String question,
    required List<String> roleKeys,
    int? expectedVersion,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.frameDeliberation(
      projectId: projectId,
      deliberationId: deliberationId,
      question: question,
      roleKeys: roleKeys,
      expectedVersion: expectedVersion,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể đóng khung nghị sự';
      return false;
    }
  }

  /// Lấy thông tin chi tiết một Deliberation.
  Future<void> loadDeliberation({
    required String projectId,
    required String deliberationId,
  }) async {
    isLoading.value = true;
    errorMessage.value = null;

    final result = await _service.getDeliberation(
      projectId: projectId,
      deliberationId: deliberationId,
    );
    isLoading.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể tải phiên nghị sự';
    }
  }

  /// Founder ghi nhận quyết định.
  Future<bool> appendDecision({
    required String projectId,
    required String deliberationId,
    required String decisionType,
    String? notes,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.appendDecision(
      projectId: projectId,
      deliberationId: deliberationId,
      decisionType: decisionType,
      notes: notes,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể ghi nhận quyết định';
      return false;
    }
  }

  /// Huỷ Deliberation.
  Future<bool> cancelDeliberation({
    required String projectId,
    required String deliberationId,
    String? reason,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.cancelDeliberation(
      projectId: projectId,
      deliberationId: deliberationId,
      reason: reason,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể huỷ phiên nghị sự';
      return false;
    }
  }
}
