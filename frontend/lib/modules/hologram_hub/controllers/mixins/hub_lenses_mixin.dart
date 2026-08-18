import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/strategy_lens_model.dart';
import '../../../../data/services/strategy_lens_service.dart';
import '../../../../data/models/evidence_model.dart';

mixin HubLensesMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  StrategyLensService get lensService;
  int? get selectedProjectIdValue;

  // ── Shared observable from HubEvidenceMixin ──────────────────────────────
  RxList<HypothesisModel> get hypothesesList;
  Future<void> loadEvidenceData(int? projectId);

  // ── Observables ──────────────────────────────────────────────────────────
  final stageLensSummary = Rxn<StageLensSummaryModel>();
  final isLensLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadStageLensesData(int? projectId) async {
    if (projectId == null) return;
    isLensLoading.value = true;
    try {
      final summary = await lensService.getStageLensSummary(projectId);
      stageLensSummary.value = summary;
    } catch (e) {
      debugPrint('Error loading stage lenses data: $e');
    } finally {
      isLensLoading.value = false;
    }
  }

  Future<void> createPestelSignal(
    PestelDimension dimension,
    String title,
    String desc,
    String impact,
    String horizon,
  ) async {
    final pid = selectedProjectIdValue;
    if (pid == null) return;
    try {
      final created = await lensService.createPestelSignal(
        projectId: pid,
        dimension: dimension,
        signalTitle: title,
        description: desc,
        impactLevel: impact,
        timeHorizon: horizon,
      );
      if (created != null) loadStageLensesData(pid);
    } catch (e) {
      debugPrint('Error creating pestel signal: $e');
    }
  }

  Future<void> convertPestelToHypothesis(int signalId) async {
    try {
      final hypo = await lensService.convertPestelToHypothesis(signalId);
      if (hypo != null) {
        hypothesesList.insert(0, hypo);
        loadStageLensesData(selectedProjectIdValue);
        loadEvidenceData(selectedProjectIdValue);
      }
    } catch (e) {
      debugPrint('Error converting pestel to hypothesis: $e');
    }
  }

  Future<void> createSwotItem(
    SwotType category,
    String statement,
    double importance,
    List<int> evidenceRefs,
  ) async {
    final pid = selectedProjectIdValue;
    if (pid == null) return;
    try {
      final created = await lensService.createSwotItem(
        projectId: pid,
        category: category,
        statement: statement,
        importance: importance,
        evidenceRefs: evidenceRefs,
      );
      if (created != null) loadStageLensesData(pid);
    } catch (e) {
      debugPrint('Error creating swot item: $e');
    }
  }

  Future<void> createTowsOption(
    TowsType quadrant,
    String title,
    String description,
  ) async {
    final pid = selectedProjectIdValue;
    if (pid == null) return;
    try {
      final created = await lensService.createTowsOption(
        projectId: pid,
        quadrant: quadrant,
        title: title,
        strategyDescription: description,
      );
      if (created != null) loadStageLensesData(pid);
    } catch (e) {
      debugPrint('Error creating tows option: $e');
    }
  }

  Future<void> convertTowsToTactics(
    int optionId,
    String tacticTitle,
    int weekNumber,
    String leadIndicator,
  ) async {
    try {
      final updated = await lensService.convertTowsToTactics(
        optionId: optionId,
        tacticTitle: tacticTitle,
        weekNumber: weekNumber,
        leadIndicator: leadIndicator,
      );
      if (updated != null) {
        loadStageLensesData(selectedProjectIdValue);
        loadEvidenceData(selectedProjectIdValue);
      }
    } catch (e) {
      debugPrint('Error converting tows to tactics: $e');
    }
  }

  Future<void> createBscGoal(
    BscPerspective perspective,
    String objective,
    String kpiName,
    String target,
    String current,
  ) async {
    final pid = selectedProjectIdValue;
    if (pid == null) return;
    try {
      final created = await lensService.createBscGoal(
        projectId: pid,
        perspective: perspective,
        objective: objective,
        kpiName: kpiName,
        targetValue: target,
        currentValue: current,
      );
      if (created != null) loadStageLensesData(pid);
    } catch (e) {
      debugPrint('Error creating bsc goal: $e');
    }
  }
}
