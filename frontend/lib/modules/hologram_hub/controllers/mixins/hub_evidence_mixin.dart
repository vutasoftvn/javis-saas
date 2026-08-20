import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../modules/vault/services/evidence_service.dart';

mixin HubEvidenceMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  EvidenceService get evidenceService;
  int? get selectedProjectIdValue;

  // ── Observables ──────────────────────────────────────────────────────────
  final hypothesesList = <HypothesisModel>[].obs;
  final evidencesList = <EvidenceModel>[].obs;
  final assumptionMatrix = Rxn<AssumptionMatrixModel>();
  final decisionsList = <StrategicDecisionModel>[].obs;
  final isEvidenceLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadEvidenceData(int? projectId) async {
    if (projectId == null) return;
    isEvidenceLoading.value = true;
    try {
      hypothesesList.value = await evidenceService.getHypotheses(
        projectId: projectId,
      );
      evidencesList.value = await evidenceService.getEvidences(
        projectId: projectId,
      );
      assumptionMatrix.value = await evidenceService.getAssumptionMatrix(
        projectId,
      );
      decisionsList.value = await evidenceService.getDecisions(
        projectId: projectId,
      );
    } catch (e) {
      debugPrint('Error loading evidence data: $e');
    } finally {
      isEvidenceLoading.value = false;
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
