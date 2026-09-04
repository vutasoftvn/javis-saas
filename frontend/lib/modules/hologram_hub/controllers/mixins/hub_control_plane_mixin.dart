import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/network/api_result.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../../../modules/workforce/models/workforce_mvp_models.dart';
import '../../../../modules/workforce/services/workforce_mvp_service.dart';
import '../../../../modules/agents/services/agent_platform_service.dart';
import '../../views/widgets/workforce_org_chart_modal.dart';
import '../../views/widgets/approval_inbox_drawer.dart';
import '../../views/widgets/work_product_inspector_modal.dart';
import '../../views/widgets/stage_roster_panel.dart';
import '../../views/widgets/exception_escalation_inbox.dart';

mixin HubControlPlaneMixin on GetxController {
  // ── Abstract service getters ─────────────────────────────────────────────
  // Task 3 — ControlPlaneService (route không canonical) đã bị thay bằng
  // WorkforceMvpService, xây trên MvpRequestClient để 404/5xx luôn ra
  // ApiFailure thay vì bị nuốt thành danh sách rỗng.
  WorkforceMvpService get workforceMvpService;
  AgentPlatformService get agentPlatformService;

  // Fix (2026-09-02, epoch-guard) — xem chú thích tại
  // `SessionController.workspaceGeneration`: các hàm `load*()` dưới đây
  // capture giá trị này NGAY TRƯỚC mỗi `await` gọi service, rồi so sánh lại
  // NGAY SAU khi await resolve — nếu khác, nghĩa là đã có switch workspace
  // hoặc logout xảy ra trong lúc chờ, discard response, không ghi vào Rx
  // state (tránh dữ liệu workspace CŨ ghi đè lên state của workspace MỚI).
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // ── Observables ──────────────────────────────────────────────────────────

  // Agent activity & pending approvals (Control Plane)
  final pendingApprovals = <WorkforceApproval>[].obs;
  final agentRuns = <WorkforceRun>[].obs;

  // COSA D2 Agent Workforce Control Plane
  final controlPlaneSummary = Rxn<Map<String, dynamic>>();
  final workforceAgents = <Map<String, dynamic>>[].obs;
  final activeApprovals = <Map<String, dynamic>>[].obs;
  final workProducts = <Map<String, dynamic>>[].obs;

  // Phase 6: Stage Roster
  final stageRoster = <Map<String, dynamic>>[].obs;
  final stageRosterMeta = Rxn<Map<String, dynamic>>();  // { stage_code, stage_name_vi, ... }
  final isStageRosterLoading = false.obs;
  final stageRosterSummary = Rxn<Map<String, dynamic>>(); // { total, high_priority, medium, locked }

  // Phase 6: Exception Escalations
  final openEscalations = <Map<String, dynamic>>[].obs;
  final hasActiveEscalations = false.obs;
  final hasCriticalEscalation = false.obs; // true nếu có FOUNDER_GATE OPEN
  final escalationSummary = Rxn<Map<String, dynamic>>(); // { total, founder_gate_count, ... }
  final isEscalationLoading = false.obs;

  // ── Data loading ─────────────────────────────────────────────────────────

  Future<void> loadPendingApprovals() async {
    final generation = _workspaceGeneration;
    final result = await workforceMvpService.listApprovals();
    if (_workspaceGeneration != generation) return;
    result.when(
      success: (data, _) => pendingApprovals.value = data,
      failure: (failure) =>
          debugPrint('[HologramHub] Error loading pending approvals: ${failure.message}'),
    );
  }

  Future<void> loadAgentRuns() async {
    final generation = _workspaceGeneration;
    final result = await workforceMvpService.listRuns(limit: 5);
    if (_workspaceGeneration != generation) return;
    result.when(
      success: (data, _) => agentRuns.value = data,
      failure: (failure) =>
          debugPrint('[HologramHub] Error loading agent runs: ${failure.message}'),
    );
  }

  Future<void> approveTaskCard(String approvalId) async {
    final result = await workforceMvpService.decideApproval(approvalId, approved: true);
    if (result is ApiSuccess<WorkforceApprovalDecision>) {
      pendingApprovals.removeWhere((a) => a.approvalId == approvalId);
    }
  }

  Future<void> rejectTaskCard(String approvalId) async {
    final result = await workforceMvpService.decideApproval(approvalId, approved: false);
    if (result is ApiSuccess<WorkforceApprovalDecision>) {
      pendingApprovals.removeWhere((a) => a.approvalId == approvalId);
    }
  }

  Future<void> loadControlPlaneSummary({bool showLoading = false}) async {
    final generation = _workspaceGeneration;
    try {
      final summary = await agentPlatformService.getDashboardSummary();
      if (_workspaceGeneration != generation) return;
      if (summary != null) controlPlaneSummary.value = summary;
    } catch (e) {
      debugPrint('[HologramHub] Error loading control plane summary: $e');
    }
  }

  Future<void> loadWorkforceAgents() async {
    final generation = _workspaceGeneration;
    try {
      final agents = await agentPlatformService.listAgents();
      if (_workspaceGeneration != generation) return;
      workforceAgents.assignAll(agents);
    } catch (e) {
      debugPrint('[HologramHub] Error loading workforce agents: $e');
    }
  }

  Future<void> loadControlPlaneApprovals() async {
    final generation = _workspaceGeneration;
    final result = await agentPlatformService.listApprovals(status: 'PENDING');
    if (_workspaceGeneration != generation) return;
    result.when(
      success: (data, _) => activeApprovals.assignAll(data),
      failure: (failure) =>
          debugPrint('[HologramHub] Error loading approvals: ${failure.message}'),
    );
  }

  Future<void> loadWorkProducts() async {
    final generation = _workspaceGeneration;
    try {
      final products = await agentPlatformService.listWorkProducts();
      if (_workspaceGeneration != generation) return;
      workProducts.assignAll(products);
    } catch (e) {
      debugPrint('[HologramHub] Error loading work products: $e');
    }
  }

  // ── Phase 6: Stage Roster Loading ────────────────────────────────────────

  /// Load Stage Roster theo stage code (ví dụ 'P2').
  /// [stageCode]: 'P0' | 'P1' | 'P2' | 'P3' | 'P4' | 'P5' | 'P6'
  Future<void> loadStageRoster(String stageCode) async {
    if (isStageRosterLoading.value) return;
    final generation = _workspaceGeneration;
    isStageRosterLoading.value = true;
    try {
      final result = await agentPlatformService.getStageRoster(stageCode);
      if (_workspaceGeneration != generation) return;
      if (result != null) {
        final roster = result['roster'] as List<dynamic>? ?? [];
        stageRoster.assignAll(
          roster.whereType<Map<String, dynamic>>().toList(),
        );
        stageRosterMeta.value = result['stage'] as Map<String, dynamic>?;
        stageRosterSummary.value = result['summary'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('[HologramHub] Error loading stage roster: $e');
    } finally {
      isStageRosterLoading.value = false;
    }
  }

  // ── Phase 6: Exception Escalation Loading ────────────────────────────────

  /// Load tất cả OPEN Exception Escalations.
  Future<void> loadOpenEscalations() async {
    if (isEscalationLoading.value) return;
    final generation = _workspaceGeneration;
    isEscalationLoading.value = true;
    try {
      final result = await agentPlatformService.listEscalations(status: 'OPEN');
      if (_workspaceGeneration != generation) return;
      final escalations = result['escalations'] as List<dynamic>? ?? [];
      openEscalations.assignAll(
        escalations.whereType<Map<String, dynamic>>().toList(),
      );

      escalationSummary.value = {
        'total': result['total'] ?? 0,
        'founder_gate_count': result['founder_gate_count'] ?? 0,
        'lead_notify_count': result['lead_notify_count'] ?? 0,
        'has_critical': result['has_critical'] ?? false,
      };
      hasActiveEscalations.value = (result['total'] as int? ?? 0) > 0;
      hasCriticalEscalation.value = result['has_critical'] == true;
    } catch (e) {
      debugPrint('[HologramHub] Error loading escalations: $e');
    } finally {
      isEscalationLoading.value = false;
    }
  }

  /// MVP hiện tại chỉ có escalations LIST (read-only) — KHÔNG có backend
  /// resolve thật (xem docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md
  /// Phase 5). UI đã vô hiệu hoá nút bấm từ 2026-09-02 (xem
  /// exception_escalation_inbox.dart) nên đường này giờ không còn ai gọi
  /// được từ UI — giữ lại làm no-op tường minh (thay vì gọi
  /// agentPlatformService.resolveEscalation vào 1 route sẽ luôn 404) để bất
  /// kỳ caller nào khác (test, tương lai) cũng nhận được thông báo rõ ràng
  /// thay vì một lỗi mạng khó hiểu.
  Future<void> resolveEscalation(
    String escalationId,
    String action, [
    String? comment,
  ]) async {
    AppToast.error(
      'Chưa hỗ trợ resolve exception trong bản này — đang chờ thiết kế domain escalation riêng.',
      title: 'Chưa khả dụng',
      duration: const Duration(seconds: 4),
    );
  }

  // ── Actions ──────────────────────────────────────────────────────────────

  Future<void> approveAgentAction(int id, [String? comment]) async {
    final result = await agentPlatformService.approveRequest(id, comment: comment);
    if (result case ApiFailure(failure: final f)) {
      // Fix-review (2026-09-02) — trước đây `approveRequest` trả `null` khi
      // lỗi và bị nuốt ở đây: Founder bấm "Duyệt", request 500/404 thật,
      // nhưng UI vẫn coi như đã duyệt xong (reload danh sách rỗng trông
      // giống "đã xử lý"). Đây là mutation rủi ro — phải báo lỗi thật, không
      // được âm thầm tiếp tục như đã thành công.
      debugPrint('[HologramHub] Error approving agent action: ${f.message}');
      AppToast.error('Không thể duyệt yêu cầu: ${f.message}');
      return;
    }
    await loadControlPlaneApprovals();
    await loadControlPlaneSummary();
  }

  Future<void> rejectAgentAction(int id, [String? comment]) async {
    final result = await agentPlatformService.rejectRequest(id, comment: comment);
    if (result case ApiFailure(failure: final f)) {
      debugPrint('[HologramHub] Error rejecting agent action: ${f.message}');
      AppToast.error('Không thể từ chối yêu cầu: ${f.message}');
      return;
    }
    await loadControlPlaneApprovals();
    await loadControlPlaneSummary();
  }

  Future<void> acceptAgentWorkProduct(int id) async {
    try {
      await agentPlatformService.acceptWorkProduct(id);
      await loadWorkProducts();
      await loadControlPlaneSummary();
    } catch (e) {
      debugPrint('[HologramHub] Error accepting work product: $e');
    }
  }

  // ── UI Modal openers ─────────────────────────────────────────────────────

  void openWorkforceModal(BuildContext context, {String? currentStageCode}) async {
    await loadWorkforceAgents();
    if (context.mounted) {
      WorkforceOrgChartModal.show(
        context,
        agents: workforceAgents,
        currentStageCode: currentStageCode,
        stageRoster: stageRoster,
        stageRosterMeta: stageRosterMeta.value,
      );
    }
  }

  void openApprovalInboxDrawer(BuildContext context) async {
    await loadControlPlaneApprovals();
    if (context.mounted) {
      ApprovalInboxDrawer.show(
        context,
        approvals: activeApprovals,
        onApprove: (id, comment) => approveAgentAction(id, comment),
        onReject: (id, comment) => rejectAgentAction(id, comment),
      );
    }
  }

  void openWorkProductModal(BuildContext context) async {
    await loadWorkProducts();
    if (context.mounted) {
      WorkProductInspectorModal.show(
        context,
        workProducts: workProducts,
        onAccept: (id) => acceptAgentWorkProduct(id),
      );
    }
  }

  /// Phase 6: Mở Stage Roster Panel (modal riêng).
  void openStageRosterModal(BuildContext context, String stageCode) async {
    await loadStageRoster(stageCode);
    if (context.mounted) {
      StageRosterModal.show(
        context,
        roster: stageRoster,
        stageMeta: stageRosterMeta.value,
        summary: stageRosterSummary.value,
        isLoading: isStageRosterLoading,
        onActivateAgent: (agentKey) => _handleAgentActivation(agentKey, stageCode),
      );
    }
  }

  /// Phase 6: Mở Exception Escalation Inbox.
  void openEscalationInbox(BuildContext context) async {
    await loadOpenEscalations();
    if (context.mounted) {
      ExceptionEscalationInbox.show(
        context,
        escalations: openEscalations,
        summary: escalationSummary.value,
        isLoading: isEscalationLoading,
        onResolve: (id, action, comment) => resolveEscalation(id, action, comment),
      );
    }
  }

  /// Xử lý khi Founder kích hoạt agent từ Stage Roster.
  /// Nếu agent bị locked → tạo STAGE_MISMATCH warning nhưng vẫn cho phép.
  Future<void> _handleAgentActivation(String agentKey, String stageCode) async {
    final agent = stageRoster.firstWhereOrNull((a) => a['key'] == agentKey);
    if (agent == null) return;

    final isLocked = agent['is_locked'] == true;
    if (isLocked) {
      // Theo Q4 trong plan: cho phép chạy nhưng tạo LEAD_NOTIFY warning
      await agentPlatformService.reportStageMismatch(
        agentKey: agentKey,
        agentName: agent['name'] ?? agentKey,
        stageCode: stageCode,
      );
      // Reload escalations để hiện badge
      await loadOpenEscalations();
    }
    // TODO: Mở task dispatch dialog sau (wire vào AgentTaskDispatcher)
  }
}
