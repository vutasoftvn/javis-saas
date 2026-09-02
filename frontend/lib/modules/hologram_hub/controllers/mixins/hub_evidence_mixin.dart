import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../modules/vault/services/evidence_service.dart';

mixin HubEvidenceMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  EvidenceService get evidenceService;
  int? get selectedProjectIdValue;

  // Fix (2026-09-02, epoch-guard full audit) — cùng cơ chế đã áp dụng ở
  // `HubControlPlaneMixin._workspaceGeneration`: `loadEvidenceData` gọi 4 API
  // tuần tự rồi ghi thẳng kết quả vào Rx state (hypotheses/evidences/
  // assumption matrix/decisions — dữ liệu tenant-specific thật). Trước đây
  // hàm này được gọi từ `HubStageMixin.loadStageContext()` (đã guard) nhưng
  // guard của caller KHÔNG tự bảo vệ các await riêng bên trong hàm được gọi —
  // capture generation NGAY TRƯỚC mỗi await, so sánh lại NGAY SAU khi await
  // resolve, discard nếu khác.
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // ── Observables ──────────────────────────────────────────────────────────
  final hypothesesList = <HypothesisModel>[].obs;
  final evidencesList = <EvidenceModel>[].obs;
  final assumptionMatrix = Rxn<AssumptionMatrixModel>();
  final decisionsList = <StrategicDecisionModel>[].obs;
  final isEvidenceLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadEvidenceData(int? projectId) async {
    if (projectId == null) return;
    final generation = _workspaceGeneration;
    isEvidenceLoading.value = true;
    try {
      final hypotheses = await evidenceService.getHypotheses(
        projectId: projectId,
      );
      if (_workspaceGeneration != generation) return;
      hypothesesList.value = hypotheses;

      final evidences = await evidenceService.getEvidences(
        projectId: projectId,
      );
      if (_workspaceGeneration != generation) return;
      evidencesList.value = evidences;

      final matrix = await evidenceService.getAssumptionMatrix(projectId);
      if (_workspaceGeneration != generation) return;
      assumptionMatrix.value = matrix;

      final decisions = await evidenceService.getDecisions(
        projectId: projectId,
      );
      if (_workspaceGeneration != generation) return;
      decisionsList.value = decisions;
    } catch (e) {
      debugPrint('Error loading evidence data: $e');
    } finally {
      if (_workspaceGeneration == generation) isEvidenceLoading.value = false;
    }
  }

  Future<void> createHypothesis(Map<String, dynamic> data) async {
    try {
      final created = await evidenceService.createHypothesis(data);
      if (created != null) {
        hypothesesList.insert(0, created);
        loadEvidenceData(selectedProjectIdValue);
      }
    } catch (e) {
      debugPrint('Error creating hypothesis: $e');
    }
  }

  Future<void> addEvidence(Map<String, dynamic> data) async {
    try {
      final created = await evidenceService.createEvidence(data);
      if (created != null) {
        evidencesList.insert(0, created);
        loadEvidenceData(selectedProjectIdValue);
      }
    } catch (e) {
      debugPrint('Error adding evidence: $e');
    }
  }

  Future<void> recordDecision(Map<String, dynamic> data) async {
    try {
      final created = await evidenceService.recordDecision(data);
      if (created != null) decisionsList.insert(0, created);
    } catch (e) {
      debugPrint('Error recording decision: $e');
    }
  }

  Future<void> searchCompanyMemory(String query) async {
    try {
      final results = await evidenceService.queryCompanyMemory(
        queryText: query,
        projectId: selectedProjectIdValue,
      );
      debugPrint('Company memory results: ${results.length}');
    } catch (e) {
      debugPrint('Error searching company memory: $e');
    }
  }
}
