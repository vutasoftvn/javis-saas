import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/services/control_plane_service.dart';
import '../../../../data/services/agent_platform_service.dart';
import '../../views/widgets/workforce_org_chart_modal.dart';
import '../../views/widgets/approval_inbox_drawer.dart';
import '../../views/widgets/work_product_inspector_modal.dart';
import '../../views/widgets/stage_roster_panel.dart';
import '../../views/widgets/exception_escalation_inbox.dart';

mixin HubControlPlaneMixin on GetxController {
  // ── Abstract service getters ─────────────────────────────────────────────
  ControlPlaneService get controlPlaneService;
  AgentPlatformService get agentPlatformService;

  // ── Observables ──────────────────────────────────────────────────────────

  // Agent activity & pending approvals (Control Plane)
  final pendingApprovals = <Map<String, dynamic>>[].obs;
  final agentRuns = <Map<String, dynamic>>[].obs;

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
    try {
      pendingApprovals.value =
          await controlPlaneService.getPendingApprovals();
    } catch (e) {
      debugPrint('[HologramHub] Error loading pending approvals: $e');
    }
  }

  Future<void> loadAgentRuns() async {
    try {
      agentRuns.value = await controlPlaneService.listRuns(limit: 5);
    } catch (e) {
      debugPrint('[HologramHub] Error loading agent runs: $e');
    }
  }

  Future<void> approveTaskCard(String approvalId) async {
    final ok = await controlPlaneService.approveAction(approvalId);
    if (ok) {
      pendingApprovals.removeWhere(
        (a) => (a['id'] ?? '').toString() == approvalId,
      );
    }
  }

  Future<void> rejectTaskCard(String approvalId) async {
    final ok = await controlPlaneService.rejectAction(approvalId);
    if (ok) {
      pendingApprovals.removeWhere(
        (a) => (a['id'] ?? '').toString() == approvalId,
      );
    }
  }

  Future<void> loadControlPlaneSummary({bool showLoading = false}) async {
    try {
      final summary = await agentPlatformService.getDashboardSummary();
      if (summary != null) controlPlaneSummary.value = summary;
    } catch (e) {
      debugPrint('[HologramHub] Error loading control plane summary: $e');
    }
  }

  Future<void> loadWorkforceAgents() async {
    try {
      workforceAgents.assignAll(await agentPlatformService.listAgents());
    } catch (e) {
      debugPrint('[HologramHub] Error loading workforce agents: $e');
    }
  }

  Future<void> loadControlPlaneApprovals() async {
    try {
      activeApprovals.assignAll(
        await agentPlatformService.listApprovals(status: 'PENDING'),
      );
    } catch (e) {
      debugPrint('[HologramHub] Error loading approvals: $e');
    }
  }

  Future<void> loadWorkProducts() async {
    try {
      workProducts.assignAll(await agentPlatformService.listWorkProducts());
    } catch (e) {
      debugPrint('[HologramHub] Error loading work products: $e');
    }
  }

  // ── Phase 6: Stage Roster Loading ────────────────────────────────────────

  /// Load Stage Roster theo stage code (ví dụ 'S2').
  /// [stageCode]: 'S0' | 'S1' | 'S2' | 'S3' | 'S4' | 'S5' | 'S6'
  Future<void> loadStageRoster(String stageCode) async {
    if (isStageRosterLoading.value) return;
    isStageRosterLoading.value = true;
    try {
      final result = await agentPlatformService.getStageRoster(stageCode);
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
    isEscalationLoading.value = true;
    try {
      final result = await agentPlatformService.listEscalations(status: 'OPEN');
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

  /// Resolve một escalation với action cụ thể và reload danh sách.
  Future<void> resolveEscalation(
    int escalationId,
    String action, [
    String? comment,
  ]) async {
    try {
      final result = await agentPlatformService.resolveEscalation(
        escalationId,
        action: action,
        comment: comment,
      );
      if (result != null) {
        // Remove from open list immediately (optimistic update)
        openEscalations.removeWhere(
          (e) => (e['id'] as int?) == escalationId,
        );
        // Reload để cập nhật summary
        await loadOpenEscalations();
        Get.snackbar(
          '✓ Đã xử lý',
          'Exception đã được resolve với action: $action',
          snackPosition: SnackPosition.BOTTOM,
          duration: const Duration(seconds: 3),
        );
      }
    } catch (e) {
      debugPrint('[HologramHub] Error resolving escalation: $e');
    }
  }

  // ── Actions ──────────────────────────────────────────────────────────────

  Future<void> approveAgentAction(int id, [String? comment]) async {
    try {
      await agentPlatformService.approveRequest(id, comment: comment);
      await loadControlPlaneApprovals();
      await loadControlPlaneSummary();
    } catch (e) {
      debugPrint('[HologramHub] Error approving agent action: $e');
    }
  }

  Future<void> rejectAgentAction(int id, [String? comment]) async {
    try {
      await agentPlatformService.rejectRequest(id, comment: comment);
      await loadControlPlaneApprovals();
      await loadControlPlaneSummary();
    } catch (e) {
      debugPrint('[HologramHub] Error rejecting agent action: $e');
    }
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
