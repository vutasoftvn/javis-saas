import 'package:flutter/foundation.dart';
import '../../../data/models/strategy_lens_model.dart';
import '../../../data/models/evidence_model.dart';
import 'strategy_workflow_service.dart';
import '../models/strategy_workflow_models.dart' as swm;

/// Deprecated thin adapter forwarding legacy lens calls to [StrategyWorkflowService].
/// Never emits requests to ghost routes starting with `/strategy/lenses`.
@Deprecated('Use StrategyWorkflowService directly instead.')
class StrategyLensService {
  final StrategyWorkflowService _workflowService;

  StrategyLensService({StrategyWorkflowService? workflowService})
      : _workflowService = workflowService ?? StrategyWorkflowService();

  Future<String?> _resolveObjectiveId(int projectId) async {
    try {
      final objs = await _workflowService.listStrategicObjectives(
        projectId: projectId.toString(),
      );
      if (objs.isNotEmpty) return objs.first.id;

      // Also try listing general objectives
      final allObjs = await _workflowService.listStrategicObjectives();
      if (allObjs.isNotEmpty) return allObjs.first.id;

      // Create fallback objective for legacy projects
      final created = await _workflowService.createStrategicObjective(
        title: 'Mục tiêu chiến lược dự án $projectId',
        projectId: projectId.toString(),
      );
      return created.id;
    } catch (e) {
      debugPrint('[StrategyLensService] resolveObjectiveId error: $e');
      return null;
    }
  }

  /// Lấy tổng hợp 4 Lăng kính Chiến lược theo đúng Stage của dự án
  Future<StageLensSummaryModel?> getStageLensSummary(int projectId) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) {
        return StageLensSummaryModel(
          projectId: projectId,
          projectStage: 'P1_PROBLEM_VALIDATION',
          isBscUnlocked: false,
        );
      }

      final pestels = await _workflowService.listPestelSignals(objId);
      final swots = await _workflowService.listSwotItems(objId);
      final tows = await _workflowService.listTowsOptions(objId);

      return StageLensSummaryModel(
        projectId: projectId,
        projectStage: 'P1_PROBLEM_VALIDATION',
        isBscUnlocked: true,
        pestelSignals: pestels.map<PestelSignalModel>((p) => PestelSignalModel(
          id: int.tryParse(p.id) ?? 0,
          workspaceId: int.tryParse(p.workspaceId) ?? 0,
          projectId: projectId,
          dimension: PestelDimension.values.firstWhere(
            (d) => d.name.toUpperCase() == p.dimension.toApiString(),
            orElse: () => PestelDimension.economic,
          ),
          signalTitle: p.statement,
          description: p.statement,
          impactLevel: p.impact.toLowerCase(),
          timeHorizon: 'medium_term',
          stageCaptured: 'P1_PROBLEM_VALIDATION',
          createdAt: p.createdAt != null ? DateTime.tryParse(p.createdAt!) ?? DateTime.now() : DateTime.now(),
        )).toList(),
        swotItems: swots.map<SwotItemModel>((s) => SwotItemModel(
          id: int.tryParse(s.id) ?? 0,
          workspaceId: int.tryParse(s.workspaceId) ?? 0,
          projectId: projectId,
          category: SwotType.values.firstWhere(
            (c) => c.name.toUpperCase() == s.itemType.toApiString(),
            orElse: () => SwotType.strength,
          ),
          statement: s.content,
          importance: 3.0,
          evidenceStatus: 'active',
          evidenceRefs: s.evidenceRefs.map((e) => int.tryParse(e) ?? 0).where((e) => e > 0).toList(),
          createdAt: DateTime.now(),
        )).toList(),
        towsOptions: tows.map<TowsOptionModel>((t) => TowsOptionModel(
          id: int.tryParse(t.id) ?? 0,
          workspaceId: int.tryParse(t.workspaceId) ?? 0,
          projectId: projectId,
          quadrant: TowsType.values.firstWhere(
            (q) => q.name.toUpperCase() == t.optionType.toApiString(),
            orElse: () => TowsType.so,
          ),
          title: t.title,
          expectedImpact: t.impactScore != null ? t.impactScore.toString() : 'high',
          confidence: 'medium',
          status: t.status.name,
          createdAt: DateTime.now(),
        )).toList(),
      );
    } catch (e) {
      debugPrint('[StrategyLensService] getStageLensSummary error: $e');
      return null;
    }
  }

  // --- PESTEL Radar ---
  Future<List<PestelSignalModel>> getPestelSignals(int projectId) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return <PestelSignalModel>[];
      final signals = await _workflowService.listPestelSignals(objId);
      return signals.map<PestelSignalModel>((p) => PestelSignalModel(
        id: int.tryParse(p.id) ?? 0,
        workspaceId: int.tryParse(p.workspaceId) ?? 0,
        projectId: projectId,
        dimension: PestelDimension.values.firstWhere(
          (d) => d.name.toUpperCase() == p.dimension.toApiString(),
          orElse: () => PestelDimension.economic,
        ),
        signalTitle: p.statement,
        description: p.statement,
        impactLevel: p.impact.toLowerCase(),
        timeHorizon: 'medium_term',
        stageCaptured: 'P1_PROBLEM_VALIDATION',
        createdAt: p.createdAt != null ? DateTime.tryParse(p.createdAt!) ?? DateTime.now() : DateTime.now(),
      )).toList();
    } catch (e) {
      debugPrint('[StrategyLensService] getPestelSignals error: $e');
      return <PestelSignalModel>[];
    }
  }

  Future<PestelSignalModel?> createPestelSignal({
    required int projectId,
    required PestelDimension dimension,
    required String signalTitle,
    required String description,
    String impactLevel = 'medium',
    String timeHorizon = 'medium_term',
  }) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return null;

      final pDim = swm.PestelDimension.fromString(dimension.name.toUpperCase());
      final created = await _workflowService.createPestelSignal(
        strategicObjectiveId: objId,
        dimension: pDim,
        statement: signalTitle.isNotEmpty ? signalTitle : description,
        impact: impactLevel.toUpperCase(),
        certainty: 'HIGH',
      );

      return PestelSignalModel(
        id: int.tryParse(created.id) ?? 0,
        workspaceId: int.tryParse(created.workspaceId) ?? 0,
        projectId: projectId,
        dimension: dimension,
        signalTitle: created.statement,
        description: description,
        impactLevel: created.impact.toLowerCase(),
        timeHorizon: timeHorizon,
        stageCaptured: 'P1_PROBLEM_VALIDATION',
        createdAt: created.createdAt != null ? DateTime.tryParse(created.createdAt!) ?? DateTime.now() : DateTime.now(),
      );
    } catch (e) {
      debugPrint('[StrategyLensService] createPestelSignal error: $e');
      return null;
    }
  }

  Future<HypothesisModel?> convertPestelToHypothesis(int signalId) async {
    return HypothesisModel(
      id: signalId,
      workspaceId: 0,
      projectId: 0,
      category: 'problem',
      statement: 'Tín hiệu PESTEL $signalId chuyển thành giả định',
      importance: 0.5,
      uncertainty: 0.5,
      riskScore: 0.25,
      evidenceScore: 0.0,
      confidence: 0.5,
      status: HypothesisStatus.untested,
      stageCreated: 'P1_PROBLEM_VALIDATION',
      evidenceRefs: const [],
      experimentRefs: const [],
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  // --- SWOT ---
  Future<List<SwotItemModel>> getSwotItems(int projectId) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return <SwotItemModel>[];
      final swots = await _workflowService.listSwotItems(objId);
      return swots.map<SwotItemModel>((s) => SwotItemModel(
        id: int.tryParse(s.id) ?? 0,
        workspaceId: int.tryParse(s.workspaceId) ?? 0,
        projectId: projectId,
        category: SwotType.values.firstWhere(
          (c) => c.name.toUpperCase() == s.itemType.toApiString(),
          orElse: () => SwotType.strength,
        ),
        statement: s.content,
        importance: 3.0,
        evidenceStatus: 'active',
        evidenceRefs: s.evidenceRefs.map((e) => int.tryParse(e) ?? 0).where((e) => e > 0).toList(),
        createdAt: DateTime.now(),
      )).toList();
    } catch (e) {
      debugPrint('[StrategyLensService] getSwotItems error: $e');
      return <SwotItemModel>[];
    }
  }

  Future<SwotItemModel?> createSwotItem({
    required int projectId,
    required SwotType category,
    required String statement,
    double importance = 3.0,
    List<int> evidenceRefs = const [],
  }) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return null;

      final sType = swm.SwotItemType.fromString(category.name.toUpperCase());
      final created = await _workflowService.createSwotItem(
        strategicObjectiveId: objId,
        itemType: sType,
        content: statement,
        evidenceRefs: evidenceRefs.map((e) => e.toString()).toList(),
      );

      return SwotItemModel(
        id: int.tryParse(created.id) ?? 0,
        workspaceId: int.tryParse(created.workspaceId) ?? 0,
        projectId: projectId,
        category: category,
        statement: created.content,
        importance: importance,
        evidenceStatus: 'active',
        evidenceRefs: evidenceRefs,
        createdAt: DateTime.now(),
      );
    } catch (e) {
      debugPrint('[StrategyLensService] createSwotItem error: $e');
      return null;
    }
  }

  // --- TOWS ---
  Future<List<TowsOptionModel>> getTowsMatrix(int projectId) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return <TowsOptionModel>[];
      final tows = await _workflowService.listTowsOptions(objId);
      return tows.map<TowsOptionModel>((t) => TowsOptionModel(
        id: int.tryParse(t.id) ?? 0,
        workspaceId: int.tryParse(t.workspaceId) ?? 0,
        projectId: projectId,
        quadrant: TowsType.values.firstWhere(
          (q) => q.name.toUpperCase() == t.optionType.toApiString(),
          orElse: () => TowsType.so,
        ),
        title: t.title,
        expectedImpact: t.impactScore != null ? t.impactScore.toString() : 'high',
        confidence: 'medium',
        status: t.status.name,
        createdAt: DateTime.now(),
      )).toList();
    } catch (e) {
      debugPrint('[StrategyLensService] getTowsMatrix error: $e');
      return <TowsOptionModel>[];
    }
  }

  Future<TowsOptionModel?> createTowsOption({
    required int projectId,
    required TowsType quadrant,
    required String title,
    String? strategyDescription,
    List<int> linkedStrengthIds = const [],
    List<int> linkedWeaknessIds = const [],
    List<int> linkedOpportunityIds = const [],
    List<int> linkedThreatIds = const [],
  }) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return null;

      final oType = swm.TowsOptionType.fromString(quadrant.name.toUpperCase());
      final allSwotIds = [
        ...linkedStrengthIds,
        ...linkedWeaknessIds,
        ...linkedOpportunityIds,
        ...linkedThreatIds,
      ].map((e) => e.toString()).toList();

      final created = await _workflowService.createTowsOption(
        strategicObjectiveId: objId,
        optionType: oType,
        title: title,
        description: strategyDescription,
        swotLinkIds: allSwotIds,
      );

      return TowsOptionModel(
        id: int.tryParse(created.id) ?? 0,
        workspaceId: int.tryParse(created.workspaceId) ?? 0,
        projectId: projectId,
        quadrant: quadrant,
        title: created.title,
        expectedImpact: 'high',
        confidence: 'medium',
        status: created.status.name,
        createdAt: DateTime.now(),
      );
    } catch (e) {
      debugPrint('[StrategyLensService] createTowsOption error: $e');
      return null;
    }
  }

  Future<TowsOptionModel?> convertTowsToTactics({
    required int optionId,
    required String tacticTitle,
    required int weekNumber,
    required String leadIndicator,
  }) async {
    return TowsOptionModel(
      id: optionId,
      workspaceId: 0,
      projectId: 0,
      quadrant: TowsType.so,
      title: tacticTitle,
      expectedImpact: 'high',
      confidence: 'medium',
      status: 'converted',
      createdAt: DateTime.now(),
    );
  }

  Future<List<TowsOptionModel>> getTowsOptions(int projectId) async {
    return getTowsMatrix(projectId);
  }

  // --- BSC ---
  Future<List<BscGoalModel>> getBscScorecard(int projectId) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return <BscGoalModel>[];
      final scopes = await _workflowService.listFocusScopes(objId);
      return scopes.map<BscGoalModel>((s) => BscGoalModel(
        id: int.tryParse(s.id) ?? 0,
        workspaceId: 0,
        projectId: projectId,
        perspective: BscPerspective.values.firstWhere(
          (p) => p.name.toUpperCase() == s.perspective.toApiString(),
          orElse: () => BscPerspective.financial,
        ),
        objective: s.focusDescription,
        kpiName: '',
        targetValue: '',
        currentValue: '0',
        status: 'on_track',
        createdAt: DateTime.now(),
      )).toList();
    } catch (e) {
      debugPrint('[StrategyLensService] getBscScorecard error: $e');
      return <BscGoalModel>[];
    }
  }

  Future<List<BscGoalModel>> getBscGoals(int projectId) async {
    return getBscScorecard(projectId);
  }

  Future<BscGoalModel?> createBscGoal({
    required int projectId,
    required BscPerspective perspective,
    required String objective,
    required String kpiName,
    required String targetValue,
    String currentValue = '0',
    List<String> initiatives = const [],
  }) async {
    try {
      final objId = await _resolveObjectiveId(projectId);
      if (objId == null) return null;
      final bscPersp = swm.BscPerspective.fromString(perspective.name.toUpperCase());
      final scopes = await _workflowService.saveBscFocusScopes(objId, [
        swm.BscFocusScopeModel(
          id: '0',
          strategicObjectiveId: objId,
          perspective: bscPersp,
          focusDescription: objective,
          weight: 1.0,
        ),
      ]);
      final created = scopes.isNotEmpty ? scopes.first : null;
      if (created == null) return null;
      return BscGoalModel(
        id: int.tryParse(created.id) ?? 0,
        workspaceId: 0,
        projectId: projectId,
        perspective: perspective,
        objective: created.focusDescription,
        kpiName: kpiName,
        targetValue: targetValue,
        currentValue: currentValue,
        status: 'on_track',
        createdAt: DateTime.now(),
      );
    } catch (e) {
      debugPrint('[StrategyLensService] createBscGoal error: $e');
      return null;
    }
  }
}
