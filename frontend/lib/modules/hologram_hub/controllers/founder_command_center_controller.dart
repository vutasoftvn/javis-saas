import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/founder_decision_model.dart';
import '../../../data/models/workforce_pack_model.dart';
import '../../../data/services/cofounder_api_service.dart';
import '../../../data/services/approvals_service.dart';

class FounderCommandCenterController extends GetxController {
  final ApprovalsService _approvalsService = ApprovalsService();

  // Reactive state
  final RxBool isLoading = false.obs;
  final Rx<CompanyPulseModel?> pulse = Rx<CompanyPulseModel?>(null);
  final RxList<NextBestActionModel> top3Actions = <NextBestActionModel>[].obs;
  final RxList<FounderDecisionModel> pendingDecisions = <FounderDecisionModel>[].obs;
  final RxList<Map<String, dynamic>> pendingApprovals = <Map<String, dynamic>>[].obs;
  final RxList<WorkforcePackModel> workforcePacks = <WorkforcePackModel>[].obs;
  final RxInt selectedTabIndex = 0.obs; // 0: Command Center, 1: AI Workforce

  // Co-Founder Chat Sheet State
  final RxList<Map<String, String>> chatMessages = <Map<String, String>>[].obs;
  final TextEditingController chatInputController = TextEditingController();
  final RxBool isChatLoading = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadDashboardData();
  }

  @override
  void onClose() {
    chatInputController.dispose();
    super.onClose();
  }

  /// Tải toàn bộ dữ liệu cho Founder Command Center
  Future<void> loadDashboardData() async {
    isLoading.value = true;
    try {
      final pulseRes = await CoFounderApiService.getCompanyPulse();
      final top3Res = await CoFounderApiService.getTop3Focus();
      final decisionsRes = await CoFounderApiService.listPendingDecisions();
      final packsRes = await CoFounderApiService.listWorkforcePacks();

      pulse.value = pulseRes;
      top3Actions.assignAll(top3Res);
      pendingDecisions.assignAll(decisionsRes);
      workforcePacks.assignAll(packsRes);

      // Load Approvals từ database thật
      try {
        final approvals = await _approvalsService.getApprovals(status: 'PENDING');
        if (approvals.isNotEmpty) {
          pendingApprovals.assignAll(approvals.map((e) => e as Map<String, dynamic>).toList());
        } else {
          pendingApprovals.clear();
        }
      } catch (_) {
        pendingApprovals.clear();
      }
    } finally {
      isLoading.value = false;
    }
  }

  /// Chốt quyết định chiến lược của Founder
  Future<void> resolveDecision({
    required int decisionId,
    required String optionKey,
    String? founderNotes,
  }) async {
    final success = await CoFounderApiService.resolveDecision(
      decisionId: decisionId,
      decisionMade: optionKey,
      founderNotes: founderNotes,
    );

    if (success) {
      pendingDecisions.removeWhere((d) => d.id == decisionId);
      Get.snackbar(
        'Đã chốt quyết định',
        'Lựa chọn đã được ghi nhận vào Decision Memory để điều phối Workforce.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }
  }

  /// Phê duyệt một Task kỹ thuật (Approval)
  ///
  /// G2 P0.7 / G3 §10.3: trước đây method này không hề gọi backend — chỉ xóa
  /// item khỏi list local và báo thành công vô điều kiện. Giờ gọi thật
  /// ApprovalsService.approve() và chỉ cập nhật UI khi backend xác nhận
  /// thành công, cùng pattern với resolveDecision()/togglePack() ở trên.
  Future<void> approveTask(dynamic approvalId) async {
    final success = await _approvalsService.approve(approvalId);
    if (success) {
      pendingApprovals.removeWhere((a) => a['id'] == approvalId);
      Get.snackbar(
        'Đã phê duyệt tác vụ',
        'Agent sẽ tiếp tục tiến trình thực thi ngay lập tức.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF3B82F6),
        colorText: Colors.white,
      );
    } else {
      Get.snackbar(
        'Không thể phê duyệt',
        'Yêu cầu phê duyệt chưa được ghi nhận ở backend. Vui lòng thử lại.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
  }

  /// Từ chối một Task kỹ thuật (Approval)
  ///
  /// G3 Phase 1E: waiting_for_you_widget.dart trước đây chỉ có nút Phê
  /// duyệt — founder muốn từ chối không có đường nào ngoài lờ đi cho tới
  /// khi hết hạn. Tái dùng đúng ApprovalsService.reject() mà module
  /// `approvals` độc lập đã dùng (approvals_controller.dart::rejectTicket),
  /// không viết UI/service reject lần thứ 5.
  Future<void> rejectTask(dynamic approvalId, String reason) async {
    final success = await _approvalsService.reject(approvalId, reason: reason);
    if (success) {
      pendingApprovals.removeWhere((a) => a['id'] == approvalId);
      Get.snackbar(
        'Đã từ chối tác vụ',
        'Lý do từ chối đã được ghi nhận.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    } else {
      Get.snackbar(
        'Không thể từ chối',
        'Yêu cầu từ chối chưa được ghi nhận ở backend. Vui lòng thử lại.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
  }

  /// Bật/Tắt một Optional Pack
  Future<void> togglePack(String packKey, bool value) async {
    final success = await CoFounderApiService.toggleOptionalPack(packKey: packKey, isActive: value);
    if (success) {
      final index = workforcePacks.indexWhere((p) => p.key == packKey);
      if (index != -1) {
        final old = workforcePacks[index];
        workforcePacks[index] = WorkforcePackModel(
          key: old.key,
          name: old.name,
          roleTitle: old.roleTitle,
          department: old.department,
          category: old.category,
          isCore: old.isCore,
          isActive: value,
          description: old.description,
          toolsCount: old.toolsCount,
        );
      }
      Get.snackbar(
        'Cập nhật Workforce Pack',
        value ? 'Đã kích hoạt gói mở rộng cho Workspace.' : 'Đã vô hiệu hóa gói mở rộng.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF6366F1),
        colorText: Colors.white,
      );
    }
  }

  /// Gửi tin nhắn trao đổi với COSA Co-Founder
  ///
  /// G2 P0.8 / G3 §10.4: khi request thất bại, trước đây hiện một câu trả
  /// lời "đã tiếp nhận và đang điều phối" giả — founder tin nhầm là tin nhắn
  /// đã được xử lý dù chưa hề tạo Mission nào. Giờ hiện đúng trạng thái lỗi.
  Future<void> sendChatMessage(String message) async {
    if (message.trim().isEmpty) return;

    chatMessages.add({'role': 'user', 'content': message});
    chatInputController.clear();
    isChatLoading.value = true;

    try {
      final res = await CoFounderApiService.chatWithCoFounder(message: message);
      final reply = res['message'] ?? 'Tôi đã tiếp nhận ý kiến của bạn.';
      chatMessages.add({'role': 'cosa', 'content': reply});
    } on CoFounderChatException catch (e) {
      chatMessages.add({
        'role': 'error',
        'content': 'Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission. (${e.message})',
      });
    } catch (e) {
      chatMessages.add({
        'role': 'error',
        'content': 'Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission.',
      });
    } finally {
      isChatLoading.value = false;
    }
  }
}
