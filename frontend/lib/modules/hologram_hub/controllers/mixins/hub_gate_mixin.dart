import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/stage_gate_model.dart';
import '../../../../data/services/stage_gate_service.dart';

mixin HubGateMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  StageGateService get stageGateService;
  int? get selectedProjectIdValue;
  Future<void> loadStageContext({int? projectId});

  // ── Observables ──────────────────────────────────────────────────────────
  final latestStageAudit = Rxn<StageGateAuditModel>();
  final prematureAlerts = <PrematureAlertModel>[].obs;
  final isStageAuditLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadStageGateData(int? projectId) async {
    if (projectId == null) return;
    try {
      final alerts = await stageGateService.getGuardrailAlerts(projectId);
      prematureAlerts.value = alerts;
    } catch (e) {
      debugPrint('Error loading stage gate data: $e');
    }
  }

  Future<void> runStageGateAudit({String? targetStage}) async {
    final pid = selectedProjectIdValue;
    if (pid == null) return;
    isStageAuditLoading.value = true;
    try {
      final audit = await stageGateService.auditStageReadiness(
        projectId: pid,
        targetStage: targetStage,
      );
      latestStageAudit.value = audit;
      loadStageGateData(pid);
    } catch (e) {
      debugPrint('Error running stage gate audit: $e');
    } finally {
      isStageAuditLoading.value = false;
    }
  }

  Future<void> applyStageTransition(int auditId, {String? rationale}) async {
    try {
      final ok = await stageGateService.applyStageTransition(
        auditId: auditId,
        rationale: rationale,
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
