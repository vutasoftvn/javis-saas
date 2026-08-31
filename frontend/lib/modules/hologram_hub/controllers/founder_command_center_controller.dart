import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/founder_decision_model.dart';
import '../../../data/models/workforce_pack_model.dart';
import '../../../modules/hologram_hub/services/cofounder_api_service.dart';
import '../../../modules/approvals/services/approvals_service.dart';
import '../../../modules/chat/services/agent_chat_service.dart';
import '../../../modules/chat/models/data_access_declaration.dart';

import '../../../core/services/secure_storage_service.dart';
import '../../../modules/strategy/services/strategy_service.dart';

class FounderCommandCenterController extends GetxController {
  final ApprovalsService _approvalsService = ApprovalsService();
  final AgentChatService _chatService = AgentChatService();

  // Task 5 (`/agent/conversations/{id}/messages`) đòi hỏi phân loại
  // `data_access` không rỗng cho mọi tin nhắn — chat sheet này là kênh trao
  // đổi business (không nhập PII), nên khai báo cố định BUSINESS_CONFIDENTIAL,
  // không cần subject_reference.
  static const _chatDataAccess = DataAccessDeclaration(
    categories: {DataAccessCategory.businessConfidential},
  );

  String? _cofounderConversationId;
  StreamSubscription<Map<String, dynamic>>? _chatSseSubscription;

  // Reactive state
  final RxBool isLoading = false.obs;
  final RxBool hasProjects = true.obs;
  final RxList<dynamic> projectsList = <dynamic>[].obs;
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
    _chatSseSubscription?.cancel();
    chatInputController.dispose();
    super.onClose();
  }

  /// Tải toàn bộ dữ liệu cho Founder Command Center
  Future<void> loadDashboardData() async {
    isLoading.value = true;
    try {
      final wsId = await SecureStorageService.read('workspace_id');
      final strategyService = StrategyService();

      List<dynamic> projects = [];
      try {
        projects = await strategyService.getProjects();
      } catch (e) {
        debugPrint('[FounderCommandCenter] getProjects error: $e');
      }

      projectsList.assignAll(projects);
      hasProjects.value = projects.isNotEmpty;

      final activeProjectId = projects.isNotEmpty ? projects.first['id'] : null;

      final pulseRes = await CoFounderApiService.getCompanyPulse(
        workspaceId: wsId,
        projectId: activeProjectId,
      );
      final top3Res = (activeProjectId != null)
          ? await CoFounderApiService.getTop3Focus(workspaceId: wsId, projectId: activeProjectId)
          : <NextBestActionModel>[];
      final decisionsRes = await CoFounderApiService.listPendingDecisions(workspaceId: wsId);
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

  /// Khởi tạo dự án đầu tiên theo flow
  Future<bool> createFirstProject({
    required String title,
    required String description,
    String stage = 'P1_PROBLEM_VALIDATION',
  }) async {
    isLoading.value = true;
    try {
      final strategyService = StrategyService();
      await strategyService.createProject(
        title: title,
        description: description,
        projectStage: stage,
        stageGoal: 'Xác thực mục tiêu trọng tâm của giai đoạn $stage',
        status: 'active',
        startDate: DateTime.now(),
      );
      await loadDashboardData();
      Get.snackbar(
        'Đã khởi tạo dự án',
        'Dự án "$title" đã được thiết lập thành công. AI Co-Founder đã sẵn sàng đồng hành!',
        snackPosition: SnackPosition.TOP,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      return true;
    } catch (e) {
      debugPrint('[FounderCommandCenter] createFirstProject error: $e');
      Get.snackbar(
        'Không thể tạo dự án',
        'Lỗi: $e',
        snackPosition: SnackPosition.TOP,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
      return false;
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
  ///
  /// Trước đây gọi `CoFounderApiService.chatWithCoFounder` → `/cofounder/chat`,
  /// một endpoint chưa từng tồn tại ở bất kỳ backend nào (luôn 404). Chat thật
  /// đi qua AgentOS conversation/message/SSE flow (`apps/cosa/api/routes.py`),
  /// đúng pattern `AgentChatService` module `chat` đã dùng — tái dùng lại thay
  /// vì tạo route giả thứ hai.
  Future<void> sendChatMessage(String message) async {
    final trimmed = message.trim();
    if (trimmed.isEmpty) return;

    chatMessages.add({'role': 'user', 'content': trimmed});
    chatInputController.clear();
    isChatLoading.value = true;

    try {
      _cofounderConversationId ??= (await _chatService.createConversation(
        title: 'Founder Command Center',
        activeAgentProfile: 'operations',
      ))
          ?.id;
      final conversationId = _cofounderConversationId;
      if (conversationId == null) {
        throw Exception('Không tạo được conversation với COSA runtime.');
      }

      final response = await _chatService.sendMessage(
        conversationId,
        content: trimmed,
        dataAccess: _chatDataAccess,
      );
      final runId = response?['run_id']?.toString();
      if (runId == null) {
        throw Exception('COSA runtime không trả về run_id.');
      }

      final assistantMsg = <String, String>{'role': 'cosa', 'content': ''};
      chatMessages.add(assistantMsg);
      _subscribeChatSse(runId, assistantMsg);
    } catch (e) {
      chatMessages.add({
        'role': 'error',
        'content': 'Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission. ($e)',
      });
      isChatLoading.value = false;
    }
  }

  void _subscribeChatSse(String runId, Map<String, String> assistantMsg) {
    _chatSseSubscription?.cancel();
    _chatSseSubscription = _chatService.streamRunEvents(runId).listen(
      (event) {
        final eventType = event['event_type']?.toString() ?? '';
        final payload = (event['payload'] as Map<String, dynamic>?) ?? {};
        switch (eventType) {
          case 'message.delta':
            final delta = payload['delta']?.toString() ?? '';
            final idx = chatMessages.indexOf(assistantMsg);
            if (idx != -1) {
              assistantMsg['content'] = (assistantMsg['content'] ?? '') + delta;
              chatMessages[idx] = assistantMsg;
            }
            break;
          case 'run.completed':
            if ((assistantMsg['content'] ?? '').isEmpty && payload['output'] != null) {
              final idx = chatMessages.indexOf(assistantMsg);
              assistantMsg['content'] = payload['output'].toString();
              if (idx != -1) chatMessages[idx] = assistantMsg;
            }
            isChatLoading.value = false;
            break;
          case 'run.failed':
          case 'run.cancelled':
            final idx = chatMessages.indexOf(assistantMsg);
            if (idx != -1) {
              assistantMsg['role'] = 'error';
              assistantMsg['content'] =
                  (assistantMsg['content'] ?? '').isEmpty ? 'Mission thất bại hoặc bị huỷ.' : assistantMsg['content']!;
              chatMessages[idx] = assistantMsg;
            }
            isChatLoading.value = false;
            break;
        }
      },
      onError: (_) => isChatLoading.value = false,
      onDone: () => isChatLoading.value = false,
    );
  }
}
