import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../data/models/stage_gate_model.dart';
import '../../../../modules/strategy/services/stage_gate_service.dart';

mixin HubGateMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  StageGateService get stageGateService;
  int? get selectedProjectIdValue;
  Future<void> loadStageContext({int? projectId});

  // Fix (2026-09-02, epoch-guard full audit) — xem chú thích tại
  // `HubControlPlaneMixin._workspaceGeneration`. `loadStageGateData` từng
  // được `loadStageContext()` (đã guard) gọi tới nhưng guard của caller
  // không tự bảo vệ await riêng của hàm này. `runStageGateAudit` là mutation
  // do người dùng chủ động bấm, NHƯNG ghi thẳng kết quả audit (dữ liệu
  // tenant-specific thật, không phải optimistic list removal) vào
  // `latestStageAudit` sau await — vẫn cần guard riêng.
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // ── Observables ──────────────────────────────────────────────────────────
  final latestStageAudit = Rxn<StageGateAuditModel>();
  final prematureAlerts = <PrematureAlertModel>[].obs;
  final isStageAuditLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadStageGateData(int? projectId) async {
    if (projectId == null) return;
    final generation = _workspaceGeneration;
    try {
      final alerts = await stageGateService.getGuardrailAlerts(projectId);
      if (_workspaceGeneration != generation) return;
      prematureAlerts.value = alerts;
    } catch (e) {
      debugPrint('Error loading stage gate data: $e');
    }
  }

  Future<void> runStageGateAudit({String? targetStage}) async {
    final pid = selectedProjectIdValue;
    if (pid == null) return;
    final generation = _workspaceGeneration;
    isStageAuditLoading.value = true;
    try {
      final audit = await stageGateService.auditStageReadiness(
        projectId: pid,
        targetStage: targetStage,
      );
      if (_workspaceGeneration != generation) return;
      latestStageAudit.value = audit;
      loadStageGateData(pid);
    } catch (e) {
      debugPrint('Error running stage gate audit: $e');
    } finally {
      if (_workspaceGeneration == generation) isStageAuditLoading.value = false;
    }
  }

  Future<void> applyStageTransition({
    dynamic projectId,
    String? toStage,
    String? reason,
    bool? override,
    String? overrideApprovalRef,
    dynamic auditId,
  }) async {
    try {
      final pid = projectId ?? selectedProjectIdValue ?? '1';
      final target = toStage ?? latestStageAudit.value?.toStage ?? 'P1_PROBLEM_VALIDATION';
      final ok = await stageGateService.applyStageTransition(
        projectId: pid,
        toStage: target,
        reason: reason,
        override: override,
        overrideApprovalRef: overrideApprovalRef,
        auditId: auditId,
      );
      if (ok) loadStageContext(projectId: selectedProjectIdValue);
    } catch (e) {
      debugPrint('Error applying stage transition: $e');
    }
  }

  void dismissPrematureAlert(int alertId) {
    prematureAlerts.removeWhere((a) => a.id == alertId);
  }
}
