import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/widgets/app_toast.dart';
import '../models/organization_api_models.dart';
import '../services/organization_service.dart';

/// Thông điệp hiển thị cho từng loại lỗi của Organization API — không bao giờ
/// đổi lỗi thành trạng thái rỗng (spec 2026-09-25 §7).
String organizationFailureMessage(ApiFailureDetail failure) {
  switch (failure.code) {
    case ApiFailureCode.unauthenticated:
      return 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.';
    case ApiFailureCode.forbidden:
      return 'Bạn không có quyền thực hiện thao tác này trong tổ chức.';
    case ApiFailureCode.notFound:
      return 'Không tìm thấy tổ chức hoặc tác tử được yêu cầu.';
    case ApiFailureCode.invalidRequest:
      return 'Dữ liệu gửi lên không hợp lệ: ${failure.message}';
    case ApiFailureCode.unavailable:
    case ApiFailureCode.notConnected:
      return 'Máy chủ tạm thời không khả dụng. Dữ liệu cũ vẫn được giữ.';
    default:
      return 'Không thể tải dữ liệu tổ chức: ${failure.message}';
  }
}

class OrganizationController extends GetxController with GetSingleTickerProviderStateMixin {
  OrganizationController({OrganizationService? service, RealtimeService? realtimeService})
      : _organizationService = service ?? OrganizationService(),
        _realtimeService = realtimeService ?? RealtimeService();

  final OrganizationService _organizationService;
  final RealtimeService _realtimeService;

  late TabController tabController;
  final isLoading = false.obs;
  final overview = Rxn<OrganizationOverview>();
  final workforce = Rxn<OrganizationWorkforce>();
  final overviewError = Rxn<ApiFailureDetail>();
  final workforceError = Rxn<ApiFailureDetail>();

  @override
  void onInit() {
    super.onInit();
    tabController = TabController(length: 2, vsync: this);
    loadOrganizationData();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  @override
  void onClose() {
    tabController.dispose();
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    // 'system.connected' fires on every (re)connect, including reconnects
    // after a dropped network - refetch then so state reconciles against the
    // durable tables instead of staying stale from before the drop.
    if (eventType.startsWith('workforce.') ||
        eventType.startsWith('approval.') ||
        eventType.startsWith('agent.') ||
        eventType == 'system.connected') {
      loadOrganizationData();
    }
  }

  /// Làm mới overview + workforce. Khi một lần làm mới thất bại, dữ liệu
  /// thành công trước đó được giữ nguyên và lỗi được hiển thị riêng.
  Future<void> loadOrganizationData() async {
    isLoading.value = true;
    try {
      final overviewResult = await _organizationService.getOverview();
      switch (overviewResult) {
        case ApiSuccess(:final data):
          overview.value = data;
          overviewError.value = null;
        case ApiFailure(:final failure):
          overviewError.value = failure;
      }

      final workforceResult = await _organizationService.listWorkforce();
      switch (workforceResult) {
        case ApiSuccess(:final data):
          workforce.value = data;
          workforceError.value = null;
        case ApiFailure(:final failure):
          workforceError.value = failure;
      }
    } finally {
      isLoading.value = false;
    }
  }

  /// Workspace agent AI có thể xếp vào sơ đồ (danh sách do server trả về).
  List<OrganizationWorkforceMember> get placeableAgents =>
      (workforce.value?.members ?? const [])
          .where((m) => m.isAi && m.workspaceAgentId != null)
          .toList(growable: false);

  bool get canManageWorkforce => overview.value?.canManageWorkforce ?? false;

  Future<bool> placeAiWorkforce({
    required String workspaceAgentId,
    required String roleTitle,
    String? managerMemberId,
  }) async {
    final result = await _organizationService.placeAiWorkforce(
      workspaceAgentId: workspaceAgentId,
      roleTitle: roleTitle,
      managerMemberId: managerMemberId,
      idempotencyKey: 'place-$workspaceAgentId-${DateTime.now().microsecondsSinceEpoch}',
    );
    switch (result) {
      case ApiSuccess(:final data):
        // Chỉ báo thành công khi server trả về member id bền vững.
        if (data.id.isEmpty) return false;
        AppToast.success(
          'Tác tử AI đã được xếp vào vị trí ${data.roleTitle}.',
          title: 'Cập nhật sơ đồ tổ chức',
        );
        await loadOrganizationData();
        return true;
      case ApiFailure(:final failure):
        debugPrint('placeAiWorkforce failed: ${failure.code} ${failure.message}');
        AppToast.error(organizationFailureMessage(failure));
        return false;
    }
  }
}
