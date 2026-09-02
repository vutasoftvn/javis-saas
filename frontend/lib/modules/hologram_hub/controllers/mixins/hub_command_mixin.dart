import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/services/secure_storage_service.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../modules/auth/services/auth_service.dart';
import '../../../../modules/dashboard/services/hub_service.dart';
import '../../../../modules/strategy/services/strategy_service.dart';
import '../../../../modules/workspace_runtime/services/workspace_runtime_service.dart';
import '../../../dashboard/controllers/dashboard_controller.dart';
import '../../views/widgets/mission_inspector_dialog.dart';
import '../../../../core/routing/app_routes.dart';

mixin HubCommandMixin on GetxController {
  // ── Abstract service getters ─────────────────────────────────────────────
  AuthService get authService;
  HubService get hubService;
  StrategyService get strategyService;
  WorkspaceRuntimeService get runtimeService;

  // Fix (2026-09-02, epoch-guard siblings) — cùng cơ chế đã áp dụng ở
  // `HubControlPlaneMixin._workspaceGeneration`: các hàm `load*()` dưới đây
  // capture giá trị này NGAY TRƯỚC mỗi `await` gọi service, rồi so sánh lại
  // NGAY SAU khi await resolve — nếu khác, đã có switch workspace hoặc
  // logout xảy ra trong lúc chờ, discard response, không ghi vào Rx state.
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // ── Observables ──────────────────────────────────────────────────────────
  final isLoading = false.obs;
  final hubSummary = Rxn<Map<String, dynamic>>();
  final commandCenterData = Rxn<Map<String, dynamic>>();

  // CEO Next Best Actions
  final ceoNextActions = <dynamic>[].obs;

  /// Lỗi tải dữ liệu list (CEO next actions, danh sách dự án...) — trước đây
  /// mọi thất bại (401/403/409/5xx, mất mạng) bị nuốt thành `[]` khiến UI
  /// hiển thị y hệt "chưa có dữ liệu". Field này expose lỗi thật để hiển thị
  /// banner/thử lại thay vì trạng thái rỗng đánh lừa người dùng.
  final RxnString dataLoadError = RxnString();

  // Founder Exception Queue
  final needsYouItems = <dynamic>[].obs;
  final resolvedProposalIds = <String>{}.obs;
  final snoozedProposalIds = <String>{}.obs;

  // Strategic Execution Loop Timeline
  final activeCycleTimeline = Rxn<Map<String, dynamic>>();

  // Mobile messages (shared with chat mixin — declared here as owner, HubChatMixin reuses)
  final mobileMessages = <Map<String, dynamic>>[].obs;
  final showMobileHistory = true.obs;
  final isChatInputActive = false.obs;

  // Strategy Navigation Sidebar
  final isStrategyNavigationExpanded = true.obs;

  // ── Chat input helpers ───────────────────────────────────────────────────
  void openChatInput() => isChatInputActive.value = true;
  void closeChatInput() => isChatInputActive.value = false;
  void toggleChatInput() => isChatInputActive.value = !isChatInputActive.value;

  // ── Strategy navigation helpers ──────────────────────────────────────────
  void toggleStrategyNavigation() =>
      isStrategyNavigationExpanded.value = !isStrategyNavigationExpanded.value;
  void expandStrategyNavigation() => isStrategyNavigationExpanded.value = true;
  void collapseStrategyNavigation() => isStrategyNavigationExpanded.value = false;

  // ── Data loading ─────────────────────────────────────────────────────────

  Future<void> loadHubSummary({bool showLoading = true}) async {
    final generation = _workspaceGeneration;
    if (showLoading) isLoading.value = true;
    try {
      final wsId = await SecureStorageService.read('workspace_id');
      if (_workspaceGeneration != generation) return;

      if (wsId == null || wsId.isEmpty) {
        final me = await authService.getMe();
        if (_workspaceGeneration != generation) return;
        if (me != null && me['display_name'] != null) {
          // userName is in HubAuthMixin — accessed via controller
        }
      }

      final data = await hubService.getHubSummary();
      if (_workspaceGeneration != generation) return;
      if (data != null) hubSummary.value = data;
      await loadNeedsYou();
    } catch (e) {
      debugPrint('Error loading hub summary: $e');
    } finally {
      if (showLoading) isLoading.value = false;
    }
  }

  Future<void> loadCommandCenterData({bool showLoading = true}) async {
    final generation = _workspaceGeneration;
    if (showLoading && commandCenterData.value == null) isLoading.value = true;
    try {
      final data = await hubService.getCommandCenterData();
      if (_workspaceGeneration != generation) return;
      if (data != null) commandCenterData.value = data;
    } catch (e) {
      debugPrint('Error loading command center data: $e');
    } finally {
      if (showLoading) isLoading.value = false;
    }
  }

  Future<void> loadCeoNextActions() async {
    final generation = _workspaceGeneration;
    try {
      final result = await strategyService.getCeoNextActions(limit: 3);
      if (_workspaceGeneration != generation) return;
      ceoNextActions.value = result.items;
      if (result.errorMessage != null) {
        dataLoadError.value = result.errorMessage;
      } else {
        // Tải thành công — xoá lỗi cũ (nếu có) để không kẹt trạng thái lỗi
        // vĩnh viễn sau một lần retry thành công.
        dataLoadError.value = null;
      }
    } catch (e) {
      debugPrint('[HologramHub] Error loading CEO next actions: $e');
      if (_workspaceGeneration != generation) return;
      dataLoadError.value = 'Không thể tải Next Best Actions: $e';
    }
  }

  Future<void> loadActiveCycleTimeline() async {
    final generation = _workspaceGeneration;
    try {
      final result = await strategyService.getTwelveWeekCycles();
      if (_workspaceGeneration != generation) return;
      if (result.errorMessage != null) {
        dataLoadError.value = result.errorMessage;
      } else {
        // Tải thành công — xoá lỗi cũ (nếu có) để không kẹt trạng thái lỗi
        // vĩnh viễn sau một lần retry thành công.
        dataLoadError.value = null;
      }
      final cycles = result.items;
      if (cycles.isNotEmpty) {
        final activeCycle = cycles.firstWhere(
          (c) => c['status'] == 'active',
          orElse: () => cycles.first,
        );
        final cycleId = activeCycle['id']?.toString();
        if (cycleId != null) {
          final timeline = await strategyService.getCycleTimeline(cycleId);
          if (_workspaceGeneration != generation) return;
          activeCycleTimeline.value = timeline;
        }
      }
    } catch (e) {
      debugPrint('[HologramHub] Error loading cycle timeline: $e');
    }
  }

  Future<void> loadNeedsYou() async {
    final generation = _workspaceGeneration;
    try {
      final items = await runtimeService.getNeedsYou();
      if (_workspaceGeneration != generation) return;
      needsYouItems.value = items;
    } catch (e) {
      debugPrint('[HologramHub] Error loading Needs You items: $e');
    }
  }

  // ── Actions ──────────────────────────────────────────────────────────────

  Future<void> handleQuickApprove(
    String approvalId,
    String decision, [
    String? reason,
  ]) async {
    if (commandCenterData.value != null) {
      final currentData = Map<String, dynamic>.from(commandCenterData.value!);
      final waitingList =
          List<dynamic>.from(currentData['waiting_for_you'] ?? []);
      waitingList.removeWhere(
        (item) => (item['approval_id']?.toString() ?? '') == approvalId,
      );
      currentData['waiting_for_you'] = waitingList;
      commandCenterData.value = currentData;
    }

    try {
      await hubService.quickApprove(
        approvalId: approvalId,
        decision: decision,
        reason: reason,
      );
      await loadCommandCenterData(showLoading: false);
    } catch (e) {
      debugPrint('Error executing quick approve: $e');
      await loadCommandCenterData(showLoading: false);
    }
  }

  Future<void> openMissionInspector(String missionId) async {
    try {
      final detail = await hubService.getMissionDetail(missionId);
      if (detail != null && Get.context != null) {
        MissionInspectorDialog.show(Get.context!, detail);
        return;
      }
    } catch (e) {
      debugPrint('openMissionInspector error: $e');
    }
    if (commandCenterData.value != null && Get.context != null) {
      final missions =
          commandCenterData.value!['active_missions'] as List<dynamic>? ?? [];
      final found = missions.firstWhereOrNull(
        (m) => m['mission_id']?.toString() == missionId,
      );
      if (found != null) {
        MissionInspectorDialog.show(
          Get.context!,
          Map<String, dynamic>.from(found as Map),
        );
        return;
      }
    }
    openDashboard(3, 0);
  }

  Future<void> togglePriorityTask(String taskId) async {
    if (commandCenterData.value != null) {
      final currentData = Map<String, dynamic>.from(commandCenterData.value!);
      final priorities =
          List<dynamic>.from(currentData['today_priorities'] ?? []);
      for (var i = 0; i < priorities.length; i++) {
        final item = Map<String, dynamic>.from(priorities[i] as Map);
        if (item['id']?.toString() == taskId) {
          final isDone = item['status'] == 'done';
          item['status'] = isDone ? 'todo' : 'done';
          priorities[i] = item;
          break;
        }
      }
      currentData['today_priorities'] = priorities;
      commandCenterData.value = currentData;
    }
  }

  Future<bool> resolveNeedsYouItem(
    String itemId, {
    String? actionName,
  }) async {
    try {
      resolvedProposalIds.add(itemId);
      snoozedProposalIds.remove(itemId);

      for (int i = 0; i < mobileMessages.length; i++) {
        final msg = Map<String, dynamic>.from(mobileMessages[i]);
        if (msg['proposals'] is List) {
          final props = (msg['proposals'] as List).map((p) {
            final pMap = Map<String, dynamic>.from(p as Map);
            if (pMap['id']?.toString() == itemId ||
                pMap['proposal_id']?.toString() == itemId) {
              pMap['status'] = 'RESOLVED';
            }
            return pMap;
          }).toList();
          msg['proposals'] = props;
          mobileMessages[i] = msg;
        }
      }
      needsYouItems.removeWhere(
        (item) => (item['id'] ?? '').toString() == itemId,
      );

      final ok = await runtimeService.resolveNeedsYou(itemId);
      if (ok) {
        await loadHubSummary(showLoading: false);
        await loadNeedsYou();
        await loadActiveCycleTimeline();

        final targetAction = actionName?.trim();
        if (targetAction != null && targetAction.isNotEmpty) {
          await executePrompt(
            'Tôi đã xác nhận & khởi tạo đề xuất: "$targetAction". '
            'Hãy xác nhận kết quả đã lưu vào hệ thống và đề xuất các bước tiếp theo cần triển khai ngay.',
          );
        }
        return true;
      }
    } catch (e) {
      debugPrint('[HologramHub] resolveNeedsYouItem error: $e');
    }
    return false;
  }

  Future<bool> snoozeNeedsYouItem(
    String itemId, {
    String? actionName,
    Duration duration = const Duration(days: 1),
  }) async {
    try {
      snoozedProposalIds.add(itemId);
      resolvedProposalIds.remove(itemId);

      for (int i = 0; i < mobileMessages.length; i++) {
        final msg = Map<String, dynamic>.from(mobileMessages[i]);
        if (msg['proposals'] is List) {
          final props = (msg['proposals'] as List).map((p) {
            final pMap = Map<String, dynamic>.from(p as Map);
            if (pMap['id']?.toString() == itemId ||
                pMap['proposal_id']?.toString() == itemId) {
              pMap['status'] = 'SNOOZED';
            }
            return pMap;
          }).toList();
          msg['proposals'] = props;
          mobileMessages[i] = msg;
        }
      }
      needsYouItems.removeWhere(
        (item) => (item['id'] ?? '').toString() == itemId,
      );

      final until = DateTime.now().add(duration);
      final ok = await runtimeService.snoozeNeedsYou(itemId, until);
      if (ok) {
        await loadNeedsYou();

        final targetAction = actionName?.trim();
        if (targetAction != null && targetAction.isNotEmpty) {
          await executePrompt(
            'Tôi đã tạm hoãn đề xuất: "$targetAction". '
            'Hãy ghi chú lại và cho tôi biết có cần điều chỉnh thông tin gì không.',
          );
        }
        return true;
      }
    } catch (e) {
      debugPrint('[HologramHub] snoozeNeedsYouItem error: $e');
    }
    return false;
  }

  // ── Navigation ───────────────────────────────────────────────────────────

  void openNeedsYou() => openDashboard(24, 1);
  void openStrategyNextActions() => openDashboard(3, 1);
  void openOkrs() => openDashboard(27, 1);
  void openTwelveWeekYear() => openDashboard(28, 1);
  void onSettingsPressed() => openDashboard(13, 4);
  void onThemeToggle() {}

  void openDashboard([int targetTab = 0, int groupIndex = 0, int strategySubTab = 0]) {
    if (Get.isRegistered<DashboardController>()) {
      final dashCtrl = Get.find<DashboardController>();
      dashCtrl.changePage(targetTab, groupIndex, strategySubTab);
    }
    Get.toNamed(AppRoutes.dashboard);
  }

  // ── Contextual panel state ───────────────────────────────────────────────

  final activeContextualPage = 'none'.obs;
  final isContextPinned = false.obs;

  void openTimelineDetail() => activeContextualPage.value = 'timeline_detail';
  void openReportDetail() => activeContextualPage.value = 'report_detail';
  void openProposalDetail() => activeContextualPage.value = 'proposal_detail';
  void openAgentActivity() => activeContextualPage.value = 'agent_activity';

  void closeContextualPage() {
    if (!isContextPinned.value) activeContextualPage.value = 'none';
  }

  void forceCloseContextualPage() {
    isContextPinned.value = false;
    activeContextualPage.value = 'none';
  }

  void togglePinContext() => isContextPinned.value = !isContextPinned.value;

  // ── Must be implemented by host (HubChatMixin) ───────────────────────────
  Future<void> executePrompt(String prompt);
}
