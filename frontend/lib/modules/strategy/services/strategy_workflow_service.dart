import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../models/strategy_workflow_models.dart';

class RevisionConflictException implements Exception {
  final String message;
  final int? currentRevision;

  RevisionConflictException(this.message, {this.currentRevision});

  @override
  String toString() => 'RevisionConflictException: $message';
}

class StrategyWorkflowService extends WorkspaceScopedService {
  void _checkResponse(dynamic response) {
    if (response.statusCode == 409) {
      String message = 'Revision conflict';
      int? currentRevision;
      try {
        final body = jsonDecode(utf8.decode(response.bodyBytes));
        if (body is Map<String, dynamic>) {
          message = body['message'] ?? message;
          currentRevision = body['currentRevision'];
        }
      } catch (_) {}
      throw RevisionConflictException(message, currentRevision: currentRevision);
    }
    if (response.statusCode >= 400) {
      String message = 'Request failed with status ${response.statusCode}';
      try {
        final body = jsonDecode(utf8.decode(response.bodyBytes));
        if (body is Map<String, dynamic> && body['message'] != null) {
          message = body['message'];
        }
      } catch (_) {}
      throw StateError(message);
    }
  }

  List<dynamic> _extractItems(dynamic decoded, [String primaryKey = 'items']) {
    if (decoded is List) return decoded;
    if (decoded is Map<String, dynamic>) {
      final items = decoded[primaryKey] ?? decoded['items'];
      if (items is List) return items;
    }
    return const [];
  }

  // --------------------------------------------------------------------------
  // 1. WORKSPACE STRATEGY SETTINGS
  // --------------------------------------------------------------------------

  Future<WorkspaceStrategySettingsModel> getWorkspaceSettings() async {
    final res = await ApiClient.get('/operations/strategy/settings');
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    final settingsMap = (data['settings'] is Map<String, dynamic>)
        ? data['settings'] as Map<String, dynamic>
        : data;
    return WorkspaceStrategySettingsModel.fromJson(settingsMap);
  }

  Future<WorkspaceStrategySettingsModel> updateWorkspaceSettings({
    WorkspaceStrategySettingsModel? settings,
    StrategyMethod? strategyMethod,
    BscMode? bscMode,
    List<BscPerspective>? enabledBscPerspectives,
    int? towsSelectionLimit,
    bool? weeklyReviewEnabled,
    MidCycleReviewPolicy? midCycleReviewPolicy,
    bool? endCycleReviewEnabled,
    List<String>? allowedAgentProfiles,
    ApprovalPolicy? approvalPolicy,
    int? expectedRevision,
  }) async {
    final method = strategyMethod ?? settings?.strategyMethod;
    final bsc = bscMode ?? settings?.bscMode;
    final bscPersp = enabledBscPerspectives ?? settings?.enabledBscPerspectives;
    final towsLimit = towsSelectionLimit ?? settings?.towsSelectionLimit;
    final weekly = weeklyReviewEnabled ?? settings?.weeklyReviewEnabled;
    final mid = midCycleReviewPolicy ?? settings?.midCycleReviewPolicy;
    final end = endCycleReviewEnabled ?? settings?.endCycleReviewEnabled;
    final agents = allowedAgentProfiles ?? settings?.allowedAgentProfiles;
    final approval = approvalPolicy ?? settings?.approvalPolicy;
    final rev = expectedRevision ?? settings?.revision;

    final body = <String, dynamic>{
      'strategyMethod': ?method?.toApiString(),
      'bscMode': ?bsc?.toApiString(),
      'enabledBscPerspectives': ?(bscPersp?.map((p) => p.toApiString()).toList()),
      'towsSelectionLimit': ?towsLimit,
      'weeklyReviewEnabled': ?weekly,
      'midCycleReviewPolicy': ?mid?.toApiString(),
      'endCycleReviewEnabled': ?end,
      'allowedAgentProfiles': ?agents,
      'approvalPolicy': ?approval?.toApiString(),
      'expectedRevision': ?rev,
    };
    final res = await ApiClient.put(
      '/operations/strategy/settings',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    final settingsMap = (data['settings'] is Map<String, dynamic>)
        ? data['settings'] as Map<String, dynamic>
        : data;
    return WorkspaceStrategySettingsModel.fromJson(settingsMap);
  }

  // --------------------------------------------------------------------------
  // 2. STRATEGIC OBJECTIVES & BSC FOCUS SCOPES
  // --------------------------------------------------------------------------

  Future<List<StrategicObjectiveModel>> listStrategicObjectives({
    String? projectId,
    String? status,
  }) async {
    final queryParams = <String>[];
    if (projectId != null && projectId.isNotEmpty) {
      queryParams.add('projectId=${Uri.encodeQueryComponent(projectId)}');
    }
    if (status != null && status.isNotEmpty) {
      queryParams.add('status=${Uri.encodeQueryComponent(status)}');
    }
    final q = queryParams.isEmpty ? '' : '?${queryParams.join('&')}';
    final res = await ApiClient.get('/operations/strategy/objectives$q');
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded);
    return items
        .map((i) => StrategicObjectiveModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  Future<StrategicObjectiveModel> createStrategicObjective({
    required String title,
    String? projectId,
    String? successDefinition,
    String? timeHorizonEnd,
    String? status,
    String? ownerMemberId,
  }) async {
    final body = <String, dynamic>{
      'title': title,
      'projectId': ?projectId,
      'successDefinition': ?successDefinition,
      'timeHorizonEnd': ?timeHorizonEnd,
      'status': ?status,
      'ownerMemberId': ?ownerMemberId,
    };
    final res = await ApiClient.post(
      '/operations/strategy/objectives',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return StrategicObjectiveModel.fromJson(data);
  }

  Future<StrategicObjectiveModel> getStrategicObjective(String id) async {
    final res = await ApiClient.get('/operations/strategy/objectives/$id');
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return StrategicObjectiveModel.fromJson(data);
  }

  Future<StrategicObjectiveModel> updateStrategicObjective(
    String id, {
    String? projectId,
    String? title,
    String? successDefinition,
    String? timeHorizonEnd,
    String? status,
    String? ownerMemberId,
    int? expectedRevision,
  }) async {
    final body = <String, dynamic>{
      'projectId': ?projectId,
      'title': ?title,
      'successDefinition': ?successDefinition,
      'timeHorizonEnd': ?timeHorizonEnd,
      'status': ?status,
      'ownerMemberId': ?ownerMemberId,
      'expectedRevision': ?expectedRevision,
    };
    final res = await ApiClient.put(
      '/operations/strategy/objectives/$id',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return StrategicObjectiveModel.fromJson(data);
  }

  Future<List<BscFocusScopeModel>> saveBscFocusScopes(
    String objectiveId,
    List<BscFocusScopeModel> scopes,
  ) async {
    final body = {
      'scopes': scopes
          .map((s) => {
                'perspective': s.perspective.toApiString(),
                'focusDescription': s.focusDescription,
                'weight': s.weight,
              })
          .toList(),
    };
    final res = await ApiClient.put(
      '/operations/strategy/objectives/$objectiveId/bsc-focus',
      body: body,
    );
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final scopesRaw = _extractItems(decoded, 'scopes');
    return scopesRaw
        .map((s) => BscFocusScopeModel.fromJson(s as Map<String, dynamic>))
        .toList();
  }

  Future<List<BscFocusScopeModel>> listFocusScopes(String objectiveId) async {
    final obj = await getStrategicObjective(objectiveId);
    return obj.bscFocusScopes;
  }

  // --------------------------------------------------------------------------
  // 3. PESTEL SIGNALS
  // --------------------------------------------------------------------------

  Future<List<PestelSignalModel>> listPestelSignals(
    String objectiveId, {
    String? status,
  }) async {
    final q = (status != null && status.isNotEmpty)
        ? '?status=${Uri.encodeQueryComponent(status)}'
        : '';
    final res = await ApiClient.get(
      '/operations/strategy/objectives/$objectiveId/analysis/pestel$q',
    );
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded);
    return items
        .map((i) => PestelSignalModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  Future<PestelSignalModel> createPestelSignal({
    required String strategicObjectiveId,
    required PestelDimension dimension,
    required String statement,
    required String impact,
    required String certainty,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'dimension': dimension.toApiString(),
      'statement': statement,
      'impact': impact,
      'certainty': certainty,
      'evidenceRefs': ?evidenceRefs,
      'bscPerspectives': ?(bscPerspectives?.map((p) => p.toApiString()).toList()),
      'status': ?status,
    };
    final res = await ApiClient.post(
      '/operations/strategy/objectives/$strategicObjectiveId/analysis/pestel',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return PestelSignalModel.fromJson(data);
  }

  Future<PestelSignalModel> updatePestelSignal(
    String objectiveId,
    String id, {
    PestelDimension? dimension,
    String? statement,
    String? impact,
    String? certainty,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'dimension': ?dimension?.toApiString(),
      'statement': ?statement,
      'impact': ?impact,
      'certainty': ?certainty,
      'evidenceRefs': ?evidenceRefs,
      'bscPerspectives': ?(bscPerspectives?.map((p) => p.toApiString()).toList()),
      'status': ?status,
    };
    final res = await ApiClient.put(
      '/operations/strategy/objectives/$objectiveId/analysis/pestel/$id',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return PestelSignalModel.fromJson(data);
  }

  // --------------------------------------------------------------------------
  // 4. RESOURCE & CAPABILITY ASSESSMENTS
  // --------------------------------------------------------------------------

  Future<List<ResourceCapabilityAssessmentModel>> listResourceCapabilities(
    String objectiveId, {
    String? status,
  }) async {
    final q = (status != null && status.isNotEmpty)
        ? '?status=${Uri.encodeQueryComponent(status)}'
        : '';
    final res = await ApiClient.get(
      '/operations/strategy/objectives/$objectiveId/analysis/resources$q',
    );
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded);
    return items
        .map((i) => ResourceCapabilityAssessmentModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  Future<ResourceCapabilityAssessmentModel> createResourceCapability({
    required String strategicObjectiveId,
    required ResourceCapabilityCategory category,
    required String statement,
    required String strengthLevel,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'category': category.toApiString(),
      'statement': statement,
      'strengthLevel': strengthLevel,
      'evidenceRefs': ?evidenceRefs,
      'bscPerspectives': ?(bscPerspectives?.map((p) => p.toApiString()).toList()),
      'status': ?status,
    };
    final res = await ApiClient.post(
      '/operations/strategy/objectives/$strategicObjectiveId/analysis/resources',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return ResourceCapabilityAssessmentModel.fromJson(data);
  }

  Future<ResourceCapabilityAssessmentModel> updateResourceCapability(
    String objectiveId,
    String id, {
    ResourceCapabilityCategory? category,
    String? statement,
    String? strengthLevel,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'category': ?category?.toApiString(),
      'statement': ?statement,
      'strengthLevel': ?strengthLevel,
      'evidenceRefs': ?evidenceRefs,
      'bscPerspectives': ?(bscPerspectives?.map((p) => p.toApiString()).toList()),
      'status': ?status,
    };
    final res = await ApiClient.put(
      '/operations/strategy/objectives/$objectiveId/analysis/resources/$id',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return ResourceCapabilityAssessmentModel.fromJson(data);
  }

  // --------------------------------------------------------------------------
  // 5. SWOT ITEMS
  // --------------------------------------------------------------------------

  Future<List<SwotItemModel>> listSwotItems(
    String objectiveId, {
    String? status,
  }) async {
    final q = (status != null && status.isNotEmpty)
        ? '?status=${Uri.encodeQueryComponent(status)}'
        : '';
    final res = await ApiClient.get(
      '/operations/strategy/objectives/$objectiveId/analysis/swot$q',
    );
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded);
    return items
        .map((i) => SwotItemModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  Future<SwotItemModel> createSwotItem({
    required String strategicObjectiveId,
    required SwotItemType itemType,
    required String content,
    String? sourceType,
    String? sourceId,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'kind': itemType.toApiString(),
      'statement': content,
      'sourceType': sourceType ?? 'MANUAL',
      'sourceId': ?sourceId,
      'evidenceRefs': ?evidenceRefs,
      'bscPerspectives': ?(bscPerspectives?.map((p) => p.toApiString()).toList()),
      'status': ?status,
    };
    final res = await ApiClient.post(
      '/operations/strategy/objectives/$strategicObjectiveId/analysis/swot',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return SwotItemModel.fromJson(data);
  }

  Future<SwotItemModel> updateSwotItem(
    String objectiveId,
    String id, {
    SwotItemType? itemType,
    String? content,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'kind': ?itemType?.toApiString(),
      'statement': ?content,
      'evidenceRefs': ?evidenceRefs,
      'bscPerspectives': ?(bscPerspectives?.map((p) => p.toApiString()).toList()),
      'status': ?status,
    };
    final res = await ApiClient.put(
      '/operations/strategy/objectives/$objectiveId/analysis/swot/$id',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return SwotItemModel.fromJson(data);
  }

  Future<List<SwotItemModel>> deriveSwotDrafts(String objectiveId) async {
    final res = await ApiClient.post(
      '/operations/strategy/objectives/$objectiveId/analysis/swot/derive-drafts',
    );
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded);
    return items
        .map((i) => SwotItemModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  // --------------------------------------------------------------------------
  // 6. TOWS OPTIONS & PRIORITIZATION
  // --------------------------------------------------------------------------

  Future<List<TowsOptionModel>> listTowsOptions(
    String objectiveId, {
    TowsOptionType? quadrant,
    TowsOptionStatus? status,
  }) async {
    final queryParams = <String>[];
    if (quadrant != null) {
      queryParams.add('quadrant=${quadrant.toApiString()}');
    }
    if (status != null) {
      queryParams.add('status=${status.toApiString()}');
    }
    final q = queryParams.isEmpty ? '' : '?${queryParams.join('&')}';
    final res = await ApiClient.get(
      '/operations/strategy/objectives/$objectiveId/tows-options$q',
    );
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded);
    return items
        .map((i) => TowsOptionModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  Future<TowsOptionModel> createTowsOption({
    required String strategicObjectiveId,
    required TowsOptionType optionType,
    required String title,
    String? description,
    List<String>? swotLinkIds,
    String? status,
  }) async {
    final body = <String, dynamic>{
      'quadrant': optionType.toApiString(),
      'title': title,
      'rationale': ?description,
      'swotItemIds': ?swotLinkIds,
      'status': ?status,
    };
    final res = await ApiClient.post(
      '/operations/strategy/objectives/$strategicObjectiveId/tows-options',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return TowsOptionModel.fromJson(data);
  }

  Future<TowsOptionModel> updateTowsOption(
    String id, {
    TowsOptionType? optionType,
    String? title,
    String? description,
    List<String>? swotLinkIds,
    int? expectedRevision,
  }) async {
    final body = <String, dynamic>{
      'quadrant': ?optionType?.toApiString(),
      'title': ?title,
      'rationale': ?description,
      'swotItemIds': ?swotLinkIds,
      'expectedRevision': ?expectedRevision,
    };
    final res = await ApiClient.put(
      '/operations/strategy/tows-options/$id',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return TowsOptionModel.fromJson(data);
  }

  Future<TowsOptionModel> evaluateTowsOption(
    String id, {
    required double impactScore,
    required double difficultyScore,
    String? rationale,
    String? scorerKind,
  }) async {
    final body = <String, dynamic>{
      'impactScore': impactScore,
      'difficultyScore': difficultyScore,
      'rationale': ?rationale,
      'scorerKind': ?scorerKind,
    };
    final res = await ApiClient.post(
      '/operations/strategy/tows-options/$id/evaluate',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return TowsOptionModel.fromJson(data);
  }

  Future<TowsOptionModel> selectTowsOption(
    String id, {
    String? strategicObjectiveId,
    String? selectionRationale,
    String? supersedeOptionId,
  }) async {
    final body = <String, dynamic>{
      'strategicObjectiveId': ?strategicObjectiveId,
      'reason': ?selectionRationale,
      'supersedeOptionId': ?supersedeOptionId,
    };
    final res = await ApiClient.post(
      '/operations/strategy/tows-options/$id/select',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return TowsOptionModel.fromJson(data);
  }

  Future<TowsOptionModel> rejectTowsOption(
    String id, {
    String? rejectionReason,
  }) async {
    final body = <String, dynamic>{
      'reason': ?rejectionReason,
    };
    final res = await ApiClient.post(
      '/operations/strategy/tows-options/$id/reject',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return TowsOptionModel.fromJson(data);
  }

  Future<TowsOptionModel> getTowsOption(String id) async {
    final res = await ApiClient.get('/operations/strategy/tows-options/$id');
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return TowsOptionModel.fromJson(data);
  }

  // --------------------------------------------------------------------------
  // 7. INITIATIVES
  // --------------------------------------------------------------------------

  Future<List<InitiativeModel>> listInitiatives({
    String? strategicObjectiveId,
    String? projectId,
    String? status,
  }) async {
    final queryParams = <String>[];
    if (strategicObjectiveId != null && strategicObjectiveId.isNotEmpty) {
      queryParams.add('strategicObjectiveId=${Uri.encodeQueryComponent(strategicObjectiveId)}');
    }
    if (projectId != null && projectId.isNotEmpty) {
      queryParams.add('projectId=${Uri.encodeQueryComponent(projectId)}');
    }
    if (status != null && status.isNotEmpty) {
      queryParams.add('status=${Uri.encodeQueryComponent(status)}');
    }
    final q = queryParams.isEmpty ? '' : '?${queryParams.join('&')}';
    final res = await ApiClient.get('/operations/initiatives$q');
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded, 'initiatives');
    return items
        .map((i) => InitiativeModel.fromJson(i as Map<String, dynamic>))
        .toList();
  }

  Future<InitiativeModel> createInitiative({
    required String title,
    String? strategicObjectiveId,
    String? sourceTowsOptionId,
    String? projectId,
    String? description,
    String? intendedOutcome,
    String? targetDate,
    List<dynamic>? milestones,
  }) async {
    final body = <String, dynamic>{
      'title': title,
      'strategicObjectiveId': ?strategicObjectiveId,
      'sourceTowsOptionId': ?sourceTowsOptionId,
      'projectId': ?projectId,
      'description': ?description,
      'intendedOutcome': ?intendedOutcome,
      'targetDate': ?targetDate,
      'milestones': ?milestones,
    };
    final res = await ApiClient.post(
      '/operations/initiatives',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return InitiativeModel.fromJson(data);
  }

  Future<InitiativeModel> getInitiative(String id) async {
    final res = await ApiClient.get('/operations/initiatives/$id');
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return InitiativeModel.fromJson(data);
  }

  Future<InitiativeModel> updateInitiative(
    String id, {
    String? title,
    String? description,
    String? intendedOutcome,
    String? targetDate,
    List<dynamic>? milestones,
    int? expectedRevision,
  }) async {
    final body = <String, dynamic>{
      'title': ?title,
      'description': ?description,
      'intendedOutcome': ?intendedOutcome,
      'targetDate': ?targetDate,
      'milestones': ?milestones,
      'expectedRevision': ?expectedRevision,
    };
    final res = await ApiClient.put(
      '/operations/initiatives/$id',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return InitiativeModel.fromJson(data);
  }

  Future<InitiativeModel> approveInitiative(
    String id, {
    String? reason,
    int? expectedRevision,
  }) async {
    final body = <String, dynamic>{
      'reason': ?reason,
      'expectedRevision': ?expectedRevision,
    };
    final res = await ApiClient.post(
      '/operations/initiatives/$id/approve',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return InitiativeModel.fromJson(data);
  }

  // --------------------------------------------------------------------------
  // 8. CYCLE REVIEWS
  // --------------------------------------------------------------------------

  Future<List<CycleReviewModel>> listCycleReviews(String cycleId) async {
    final res = await ApiClient.get('/operations/cycles/$cycleId/reviews');
    _checkResponse(res);
    final decoded = jsonDecode(utf8.decode(res.bodyBytes));
    final items = _extractItems(decoded, 'reviews');
    return items
        .map((r) => CycleReviewModel.fromJson(r as Map<String, dynamic>))
        .toList();
  }

  Future<CycleReviewModel> getCycleReview(String reviewId) async {
    final res = await ApiClient.get('/operations/cycle-reviews/$reviewId');
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return CycleReviewModel.fromJson(data);
  }

  Future<CycleReviewModel> startCycleReview(String reviewId) async {
    final res = await ApiClient.post('/operations/cycle-reviews/$reviewId/start');
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return CycleReviewModel.fromJson(data);
  }

  Future<CycleReviewModel> updateCycleReview(
    String reviewId, {
    String? conclusion,
  }) async {
    final body = <String, dynamic>{
      'conclusion': ?conclusion,
    };
    final res = await ApiClient.patch(
      '/operations/cycle-reviews/$reviewId',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return CycleReviewModel.fromJson(data);
  }

  Future<CycleReviewModel> createCustomMidCycleReview(
    String cycleId,
    int scheduledWeekNo,
  ) async {
    final res = await ApiClient.post(
      '/operations/cycles/$cycleId/reviews/custom-mid-cycle',
      body: {'scheduledWeekNo': scheduledWeekNo},
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return CycleReviewModel.fromJson(data);
  }

  Future<CycleReviewModel> closeCycleReview(
    String reviewId, {
    String? conclusion,
    String? decisionId,
  }) async {
    final body = <String, dynamic>{
      'conclusion': ?conclusion,
      'decisionId': ?decisionId,
    };
    final res = await ApiClient.post(
      '/operations/cycle-reviews/$reviewId/close',
      body: body,
    );
    _checkResponse(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return CycleReviewModel.fromJson(data);
  }
}
