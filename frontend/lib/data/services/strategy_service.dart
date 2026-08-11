import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

/// Lỗi từ Strategy API (422 validate, 403 thiếu quyền, 409 sai trạng thái revision...)
class StrategyApiException implements Exception {
  final int statusCode;
  final String message;
  StrategyApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class StrategyService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<String> _requireWorkspaceId() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      throw StrategyApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

  dynamic _decode(dynamic response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {
      // giữ nguyên detail mặc định nếu body không phải JSON hợp lệ
    }
    throw StrategyApiException(response.statusCode, detail);
  }

  List<dynamic> _decodeList(dynamic response, String key) {
    if (response.statusCode == 404) return [];
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return [];
      try {
        final data = jsonDecode(response.body);
        return data is Map && data[key] is List ? (data[key] as List<dynamic>) : [];
      } catch (_) {
        return [];
      }
    }
    return [];
  }

  // ====================================================================
  // Strategic Canvas & Foundation (Phase 1)
  // ====================================================================

  Future<List<dynamic>> getCanvases() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/strategy/canvases?workspace_id=$workspaceId');
      return _decodeList(response, 'canvases');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> getCanvasDetail(String canvasId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get('/strategy/canvases/$canvasId?workspace_id=$workspaceId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> createCanvas(String name, {String? description}) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases?workspace_id=$workspaceId',
      body: {
        'name': name,
        'description': ?description,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateCanvas(String canvasId, {String? name, String? description}) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/canvases/$canvasId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'description': ?description,
      },
    );
    return _decode(response);
  }

  Future<void> deleteCanvas(String canvasId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/canvases/$canvasId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<Map<String, dynamic>> generateAiFoundation(String canvasId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post('/strategy/canvases/$canvasId/generate-ai-foundation?workspace_id=$workspaceId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> createRevision(String canvasId, {String? baseRevisionId}) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases/$canvasId/revisions?workspace_id=$workspaceId',
      body: {
        'base_revision_id': ?baseRevisionId,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> getRevisionDetail(String revisionId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get('/strategy/revisions/$revisionId?workspace_id=$workspaceId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> submitReview(String revisionId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post('/strategy/revisions/$revisionId/submit-review?workspace_id=$workspaceId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> approveRevision(String revisionId, {String? note}) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/approve?workspace_id=$workspaceId',
      body: {
        'note': ?note,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> requestChanges(String revisionId, String reason) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/request-changes?workspace_id=$workspaceId',
      body: {'reason': reason},
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> saveFoundation(
    String revisionId, {
    required String vision,
    required String mission,
    required List<Map<String, dynamic>> values,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/revisions/$revisionId/foundation?workspace_id=$workspaceId',
      body: {'vision': vision, 'mission': mission, 'values': values},
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> createContextPack(
    String revisionId, {
    Map<String, dynamic>? businessContext,
    Map<String, dynamic>? internalResources,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/context-packs?workspace_id=$workspaceId',
      body: {
        'business_context': ?businessContext,
        'internal_resources': ?internalResources,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateContextPack(
    String contextPackId, {
    Map<String, dynamic>? businessContext,
    Map<String, dynamic>? internalResources,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/context-packs/$contextPackId?workspace_id=$workspaceId',
      body: {
        'business_context': ?businessContext,
        'internal_resources': ?internalResources,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> linkEvidence(String contextPackId, List<String> evidenceIds) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/context-packs/$contextPackId/evidence?workspace_id=$workspaceId',
      body: {'evidence_ids': evidenceIds},
    );
    final data = _decode(response);
    return data?['linked'] ?? [];
  }

  Future<Map<String, dynamic>> approveContextPack(String contextPackId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post('/strategy/context-packs/$contextPackId/approve?workspace_id=$workspaceId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> createEvidence({
    required String title,
    required String summary,
    required String sourceType,
    required String reliability,
    String? sourceUrlOrVaultUri,
    DateTime? publishedAt,
    List<String>? tags,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/evidence?workspace_id=$workspaceId',
      body: {
        'title': title,
        'summary': summary,
        'source_type': sourceType,
        'reliability': reliability,
        'source_url_or_vault_uri': ?sourceUrlOrVaultUri,
        'published_at': ?publishedAt?.toIso8601String(),
        'tags': ?tags,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getEvidence({String? sourceType, String? reliability, String? tag}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final params = {
      'workspace_id': workspaceId,
      'source_type': ?sourceType,
      'reliability': ?reliability,
      'tag': ?tag,
    };
    final query = Uri(queryParameters: params).query;
    try {
      final response = await ApiClient.get('/strategy/evidence?$query');
      return _decodeList(response, 'evidence');
    } catch (_) {
      return [];
    }
  }

  // ====================================================================
  // OKRs & Key Results
  // ====================================================================

  Future<List<dynamic>> getOkrCycles() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/okrs/cycles?workspace_id=$workspaceId');
      return _decodeList(response, 'cycles');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createOkrCycle({
    required String name,
    DateTime? startDate,
    DateTime? endDate,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/okrs/cycles?workspace_id=$workspaceId',
      body: {
        'name': name,
        'start_date': ?startDate?.toIso8601String(),
        'end_date': ?endDate?.toIso8601String(),
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getObjectives({String? cycleId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final query = cycleId != null ? 'workspace_id=$workspaceId&cycle_id=$cycleId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/okrs/objectives?$query');
      return _decodeList(response, 'objectives');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createObjective({
    required String title,
    String? cycleId,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/okrs/objectives?workspace_id=$workspaceId',
      body: {
        'title': title,
        if (cycleId != null && cycleId.isNotEmpty) 'cycle_id': cycleId,
        if (status != null && status.isNotEmpty) 'status': status,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateObjective(
    String objectiveId, {
    String? title,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/okrs/objectives/$objectiveId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<void> deleteObjective(String objectiveId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/okrs/objectives/$objectiveId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<List<dynamic>> getKeyResults({String? objectiveId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final query = objectiveId != null ? 'workspace_id=$workspaceId&objective_id=$objectiveId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/okrs/key-results?$query');
      return _decodeList(response, 'key_results');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createKeyResult({
    required String objectiveId,
    String? title,
    double? baselineValue,
    double? currentValue,
    double? targetValue,
    String? unit,
    String? cadence,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/okrs/key-results?workspace_id=$workspaceId',
      body: {
        'objective_id': objectiveId,
        if (title != null && title.isNotEmpty) 'title': title,
        'baseline_value': baselineValue ?? 0.0,
        'current_value': currentValue ?? 0.0,
        'target_value': targetValue ?? 100.0,
        'unit': unit ?? '%',
        'cadence': cadence ?? 'weekly',
        'status': status ?? 'active',
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateKeyResult(
    String keyResultId, {
    double? currentValue,
    double? targetValue,
    String? unit,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/okrs/key-results/$keyResultId?workspace_id=$workspaceId',
      body: {
        'current_value': ?currentValue,
        'target_value': ?targetValue,
        'unit': ?unit,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/okrs/key-results/$keyResultId?workspace_id=$workspaceId');
    _decode(response);
  }

  // ====================================================================
  // 12-Week Execution Plans & Commitments
  // ====================================================================

  Future<List<dynamic>> getTwelveWeekCycles() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/execution/twelve-week-cycles?workspace_id=$workspaceId');
      return _decodeList(response, 'cycles');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createTwelveWeekCycle({
    required String theme,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles?workspace_id=$workspaceId',
      body: {
        'theme': theme,
        'start_date': ?startDate?.toIso8601String(),
        'end_date': ?endDate?.toIso8601String(),
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getWeeklyPlans({String? cycleId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final query = cycleId != null ? 'workspace_id=$workspaceId&cycle_id=$cycleId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/execution/weekly-plans?$query');
      return _decodeList(response, 'plans');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createWeeklyPlan({
    required int weekNo,
    String? cycleId,
    String? focus,
    DateTime? startDate,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/weekly-plans?workspace_id=$workspaceId',
      body: {
        'week_no': weekNo,
        'cycle_id': ?cycleId,
        'focus': ?focus,
        'start_date': ?startDate?.toIso8601String(),
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateWeeklyPlan(
    String planId, {
    String? focus,
    double? executionScore,
    String? reflection,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/weekly-plans/$planId?workspace_id=$workspaceId',
      body: {
        'focus': ?focus,
        'execution_score': ?executionScore,
        'reflection': ?reflection,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getWeeklyCommitments({String? weeklyPlanId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final query = weeklyPlanId != null ? 'workspace_id=$workspaceId&weekly_plan_id=$weeklyPlanId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/execution/weekly-commitments?$query');
      return _decodeList(response, 'commitments');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createWeeklyCommitment({
    required String weeklyPlanId,
    required String title,
    String? plannedEffort,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/weekly-commitments?workspace_id=$workspaceId',
      body: {
        'weekly_plan_id': weeklyPlanId,
        'title': title,
        'planned_effort': plannedEffort ?? 'medium',
        'status': status ?? 'todo',
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateWeeklyCommitment(
    String commitmentId, {
    String? title,
    String? status,
    String? plannedEffort,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/weekly-commitments/$commitmentId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'status': ?status,
        'planned_effort': ?plannedEffort,
      },
    );
    return _decode(response);
  }

  Future<void> deleteWeeklyCommitment(String commitmentId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/execution/weekly-commitments/$commitmentId?workspace_id=$workspaceId');
    _decode(response);
  }

  // ====================================================================
  // Strategic Analysis (PESTEL, SWOT, TOWS) & AI Generator
  // ====================================================================

  Future<List<dynamic>> getPestelItems() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/strategy/analyses/pestel?workspace_id=$workspaceId');
      return _decodeList(response, 'items');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createPestelItem({
    required String factor,
    required String statement,
    String? impact,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analyses/pestel?workspace_id=$workspaceId',
      body: {
        'factor': factor,
        'statement': statement,
        'impact': impact ?? 'Medium',
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updatePestelItem(
    String itemId, {
    String? factor,
    String? statement,
    String? impact,
    String? horizon,
    String? confidence,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final body = <String, dynamic>{};
    if (factor != null) body['factor'] = factor;
    if (statement != null) body['statement'] = statement;
    if (impact != null) body['impact'] = impact;
    if (horizon != null) body['horizon'] = horizon;
    if (confidence != null) body['confidence'] = confidence;

    final response = await ApiClient.put(
      '/strategy/analyses/pestel/$itemId?workspace_id=$workspaceId',
      body: body,
    );
    return _decode(response);
  }

  Future<void> deletePestelItem(String itemId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/analyses/pestel/$itemId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<List<dynamic>> getSwotItems() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/strategy/analyses/swot?workspace_id=$workspaceId');
      return _decodeList(response, 'items');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createSwotItem({
    required String category,
    required String statement,
    String? impact,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analyses/swot?workspace_id=$workspaceId',
      body: {
        'category': category,
        'statement': statement,
        'impact': impact ?? 'High',
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateSwotItem(
    String itemId, {
    String? category,
    String? statement,
    String? impact,
    String? likelihood,
    String? confidence,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final body = <String, dynamic>{};
    if (category != null) body['category'] = category;
    if (statement != null) body['statement'] = statement;
    if (impact != null) body['impact'] = impact;
    if (likelihood != null) body['likelihood'] = likelihood;
    if (confidence != null) body['confidence'] = confidence;

    final response = await ApiClient.put(
      '/strategy/analyses/swot/$itemId?workspace_id=$workspaceId',
      body: body,
    );
    return _decode(response);
  }

  Future<void> deleteSwotItem(String itemId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/analyses/swot/$itemId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<List<dynamic>> getTowsOptions() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/strategy/analyses/tows?workspace_id=$workspaceId');
      return _decodeList(response, 'options');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createTowsOption({
    required String quadrant,
    required String title,
    required String tradeoffs,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analyses/tows?workspace_id=$workspaceId',
      body: {
        'quadrant': quadrant,
        'title': title,
        'tradeoffs': tradeoffs,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateTowsOption(
    String optionId, {
    String? quadrant,
    String? title,
    String? tradeoffs,
    String? expectedImpact,
    String? confidence,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final body = <String, dynamic>{};
    if (quadrant != null) body['quadrant'] = quadrant;
    if (title != null) body['title'] = title;
    if (tradeoffs != null) body['tradeoffs'] = tradeoffs;
    if (expectedImpact != null) body['expected_impact'] = expectedImpact;
    if (confidence != null) body['confidence'] = confidence;
    if (status != null) body['status'] = status;

    final response = await ApiClient.put(
      '/strategy/analyses/tows/$optionId?workspace_id=$workspaceId',
      body: body,
    );
    return _decode(response);
  }

  Future<void> deleteTowsOption(String optionId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/analyses/tows/$optionId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<Map<String, dynamic>> getPromptTemplate() async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get('/strategy/analyses/prompt-template?workspace_id=$workspaceId');
    return _decode(response) ?? {};
  }

  Future<Map<String, dynamic>> updatePromptTemplate({
    String? templateContent,
    int? pestelItemsPerFactor,
    int? swotItemsPerCategory,
    int? towsItemsPerQuadrant,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final body = <String, dynamic>{};
    if (templateContent != null) body['template_content'] = templateContent;
    if (pestelItemsPerFactor != null) body['pestel_items_per_factor'] = pestelItemsPerFactor;
    if (swotItemsPerCategory != null) body['swot_items_per_category'] = swotItemsPerCategory;
    if (towsItemsPerQuadrant != null) body['tows_items_per_quadrant'] = towsItemsPerQuadrant;

    final response = await ApiClient.put(
      '/strategy/analyses/prompt-template?workspace_id=$workspaceId',
      body: body,
    );
    return _decode(response) ?? {};
  }

  Future<Map<String, dynamic>> resetPromptTemplate() async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post('/strategy/analyses/prompt-template/reset?workspace_id=$workspaceId');
    return _decode(response) ?? {};
  }

  Future<Map<String, dynamic>> generateAiAnalysis({
    String? projectId,
    String? focusArea,
    bool clearExisting = true,
    int? pestelItemsPerFactor,
    int? swotItemsPerCategory,
    int? towsItemsPerQuadrant,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final body = <String, dynamic>{
      'clear_existing': clearExisting,
    };
    if (projectId != null && projectId.isNotEmpty) {
      body['project_id'] = projectId;
    }
    if (focusArea != null && focusArea.isNotEmpty) {
      body['focus_area'] = focusArea;
    }
    if (pestelItemsPerFactor != null) {
      body['pestel_items_per_factor'] = pestelItemsPerFactor;
    }
    if (swotItemsPerCategory != null) {
      body['swot_items_per_category'] = swotItemsPerCategory;
    }
    if (towsItemsPerQuadrant != null) {
      body['tows_items_per_quadrant'] = towsItemsPerQuadrant;
    }

    final response = await ApiClient.post(
      '/strategy/analyses/generate-ai?workspace_id=$workspaceId',
      body: body,
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> generateAiOkrs({
    String? towsId,
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final body = <String, dynamic>{
      'objectives_count': objectivesCount,
      'krs_per_objective_count': krsPerObjectiveCount,
    };
    if (towsId != null && towsId.isNotEmpty) {
      body['tows_id'] = towsId;
    }
    if (cycleId != null && cycleId.isNotEmpty) {
      body['cycle_id'] = cycleId;
    }

    final response = await ApiClient.post(
      '/okrs/generate-ai?workspace_id=$workspaceId',
      body: body,
    );
    return _decode(response);
  }

  // ====================================================================
  // Strategic Projects & Initiatives
  // ====================================================================

  Future<List<dynamic>> getProjects() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/strategy/projects?workspace_id=$workspaceId');
      return _decodeList(response, 'projects');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createProject({
    required String title,
    String? phase,
    String? currentGate,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects?workspace_id=$workspaceId',
      body: {
        'title': title,
        'phase': ?phase,
        'current_gate': ?currentGate,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateProject(
    String projectId, {
    String? title,
    String? phase,
    String? currentGate,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/projects/$projectId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'phase': ?phase,
        'current_gate': ?currentGate,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<void> deleteProject(String projectId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/projects/$projectId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<List<dynamic>> getInitiatives({String? projectId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final query = projectId != null ? 'workspace_id=$workspaceId&project_id=$projectId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/strategy/initiatives?$query');
      return _decodeList(response, 'initiatives');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createInitiative({
    required String title,
    String? projectId,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/initiatives?workspace_id=$workspaceId',
      body: {
        'title': title,
        'project_id': ?projectId,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateInitiative(
    String initiativeId, {
    String? title,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/initiatives/$initiativeId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<void> deleteInitiative(String initiativeId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/initiatives/$initiativeId?workspace_id=$workspaceId');
    _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Single Project Journey & Assisted Terra
  // ====================================================================

  Future<Map<String, dynamic>> classifyProject(
    String projectId, {
    String? titleOverride,
    String? descriptionOverride,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/classify?workspace_id=$workspaceId',
      body: {
        'title_override': ?titleOverride,
        'description_override': ?descriptionOverride,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> getMethodologyPlan(String projectId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/projects/$projectId/methodology?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> routeMethodology(
    String projectId, {
    List<String>? customMethodologies,
    String? rationaleOverride,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/methodology?workspace_id=$workspaceId',
      body: {
        'custom_methodologies': ?customMethodologies,
        'rationale_override': ?rationaleOverride,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> exportAnalysisPrompt({
    String? projectId,
    String? canvasId,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analysis/export?workspace_id=$workspaceId',
      body: {
        'project_id': ?projectId,
        'canvas_id': ?canvasId,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> importAnalysisResult(
    String rawInput, {
    String? projectId,
    String? canvasId,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analysis/import?workspace_id=$workspaceId',
      body: {
        'raw_input': rawInput,
        'project_id': ?projectId,
        'canvas_id': ?canvasId,
      },
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 13-Week Execution Engine & Stage-Gate Governance (Sprint 3)
  // ====================================================================

  Future<List<dynamic>> getCycleStages(String cycleId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get('/execution/twelve-week-cycles/$cycleId/stages?workspace_id=$workspaceId');
      return _decodeList(response, 'stages');
    } catch (_) {
      return [];
    }
  }

  Future<List<dynamic>> generateStandardCycleStages(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/stages/generate-standard?workspace_id=$workspaceId',
    );
    return _decodeList(response, 'stages');
  }

  Future<Map<String, dynamic>> createCycleStage(
    String cycleId, {
    required String name,
    required int startWeek,
    required int endWeek,
    required int orderNo,
    String? purpose,
    Map<String, dynamic>? expectedOutcomes,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/stages?workspace_id=$workspaceId',
      body: {
        'name': name,
        'start_week': startWeek,
        'end_week': endWeek,
        'order_no': orderNo,
        'purpose': ?purpose,
        'expected_outcomes': ?expectedOutcomes,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateCycleStage(
    String stageId, {
    String? name,
    String? purpose,
    int? startWeek,
    int? endWeek,
    String? status,
    Map<String, dynamic>? expectedOutcomes,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/stages/$stageId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'purpose': ?purpose,
        'start_week': ?startWeek,
        'end_week': ?endWeek,
        'status': ?status,
        'expected_outcomes': ?expectedOutcomes,
      },
    );
    return _decode(response);
  }

  Future<void> deleteCycleStage(String stageId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/execution/stages/$stageId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<List<dynamic>> getMilestones({String? cycleId, String? stageId, String? projectId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final params = <String>['workspace_id=$workspaceId'];
    if (cycleId != null) params.add('cycle_id=$cycleId');
    if (stageId != null) params.add('stage_id=$stageId');
    if (projectId != null) params.add('project_id=$projectId');
    try {
      final response = await ApiClient.get('/execution/milestones?${params.join('&')}');
      return _decodeList(response, 'milestones');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createMilestone({
    required String name,
    String? cycleId,
    String? stageId,
    String? projectId,
    String? description,
    int? dueWeek,
    String? acceptanceCriteria,
    Map<String, dynamic>? requiredArtifacts,
    Map<String, dynamic>? requiredMetrics,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/milestones?workspace_id=$workspaceId',
      body: {
        'name': name,
        'cycle_id': ?cycleId,
        'stage_id': ?stageId,
        'project_id': ?projectId,
        'description': ?description,
        'due_week': ?dueWeek,
        'acceptance_criteria': ?acceptanceCriteria,
        'required_artifacts': ?requiredArtifacts,
        'required_metrics': ?requiredMetrics,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateMilestone(
    String milestoneId, {
    String? name,
    String? description,
    int? dueWeek,
    String? status,
    String? acceptanceCriteria,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/milestones/$milestoneId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'description': ?description,
        'due_week': ?dueWeek,
        'status': ?status,
        'acceptance_criteria': ?acceptanceCriteria,
      },
    );
    return _decode(response);
  }

  Future<void> deleteMilestone(String milestoneId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/execution/milestones/$milestoneId?workspace_id=$workspaceId');
    _decode(response);
  }

  Future<Map<String, dynamic>> linkMilestoneEvidence(
    String milestoneId,
    String evidenceId, {
    String? relevanceNote,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/milestones/$milestoneId/evidence?workspace_id=$workspaceId',
      body: {
        'evidence_id': evidenceId,
        'relevance_note': ?relevanceNote,
      },
    );
    return _decode(response);
  }

  Future<void> unlinkMilestoneEvidence(String milestoneId, String evidenceId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete(
      '/execution/milestones/$milestoneId/evidence/$evidenceId?workspace_id=$workspaceId',
    );
    _decode(response);
  }

  Future<List<dynamic>> getGateDecisions({String? projectId, String? stageId, String? milestoneId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    final params = <String>['workspace_id=$workspaceId'];
    if (projectId != null) params.add('project_id=$projectId');
    if (stageId != null) params.add('stage_id=$stageId');
    if (milestoneId != null) params.add('milestone_id=$milestoneId');
    try {
      final response = await ApiClient.get('/execution/gate-decisions?${params.join('&')}');
      return _decodeList(response, 'gate_decisions');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> recordGateDecision({
    required String projectId,
    required String decision,
    required String rationale,
    String? milestoneId,
    String? stageId,
    String? evidenceSummary,
    String? nextStepInstructions,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/gate-decisions?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'decision': decision,
        'rationale': rationale,
        'milestone_id': ?milestoneId,
        'stage_id': ?stageId,
        'evidence_summary': ?evidenceSummary,
        'next_step_instructions': ?nextStepInstructions,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>?> getCycleContract(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/contract?workspace_id=$workspaceId',
      );
      return _decode(response);
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>> upsertCycleContract(
    String cycleId, {
    required String successDefinition,
    double? founderCapacityPerWeek,
    double? reservedBufferPercent,
    double? aiBudget,
    double? operatingBudget,
    List<String>? goalIds,
    List<String>? krIds,
    String? status,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/contract?workspace_id=$workspaceId',
      body: {
        'success_definition': successDefinition,
        'founder_capacity_per_week': ?founderCapacityPerWeek,
        'reserved_buffer_percent': ?reservedBufferPercent,
        'ai_budget': ?aiBudget,
        'operating_budget': ?operatingBudget,
        'goal_ids': ?goalIds,
        'kr_ids': ?krIds,
        'status': ?status,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateWeeklyMission(
    String planId, {
    String? mission,
    Map<String, dynamic>? successCriteria,
    String? stageId,
    double? outcomeScore,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/weekly-plans/$planId/mission?workspace_id=$workspaceId',
      body: {
        'mission': ?mission,
        'success_criteria': ?successCriteria,
        'stage_id': ?stageId,
        'outcome_score': ?outcomeScore,
      },
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Planning Compiler → V10 Runtime (Sprint 4)
  // ====================================================================

  Future<Map<String, dynamic>> compileCycle(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/compile?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> compileWeeklyPlan(String planId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/weekly-plans/$planId/compile?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> getCycleCompilationStatus(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get(
      '/execution/twelve-week-cycles/$cycleId/compilation-status?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Weekly Review & Week 13 Strategic Transition (Sprint 5)
  // ====================================================================

  Future<Map<String, dynamic>> createWeeklyReview(
    String cycleId, {
    required String weeklyPlanId,
    required double executionScore,
    required double outcomeScore,
    String? evidenceLearned,
    Map<String, dynamic>? assumptionsConfirmed,
    Map<String, dynamic>? assumptionsInvalidated,
    String? recommendation,
    String? narrativeSummary,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/weekly-reviews?workspace_id=$workspaceId',
      body: {
        'weekly_plan_id': weeklyPlanId,
        'execution_score': executionScore,
        'outcome_score': outcomeScore,
        'evidence_learned': ?evidenceLearned,
        'assumptions_confirmed': ?assumptionsConfirmed,
        'assumptions_invalidated': ?assumptionsInvalidated,
        'recommendation': ?recommendation,
        'narrative_summary': ?narrativeSummary,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getWeeklyReviews(String cycleId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/weekly-reviews?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'weekly_reviews');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>?> getWeeklyPlanReview(String planId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/weekly-plans/$planId/review?workspace_id=$workspaceId',
      );
      return _decode(response);
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>> finalizeWeek13(
    String cycleId, {
    required double overallExecutionScore,
    required double overallOutcomeScore,
    required double okrAchievementRate,
    String? strategicLearnings,
    String? systemicBlockers,
    Map<String, dynamic>? portfolioAdjustments,
    String? nextCycleRecommendations,
    String? celebrationTitle,
    Map<String, dynamic>? milestonesAchieved,
    Map<String, dynamic>? topPerformersRecognized,
    String? rewardsOrRituals,
    String? reflectionNotes,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/week13/finalize?workspace_id=$workspaceId',
      body: {
        'overall_execution_score': overallExecutionScore,
        'overall_outcome_score': overallOutcomeScore,
        'okr_achievement_rate': okrAchievementRate,
        'strategic_learnings': ?strategicLearnings,
        'systemic_blockers': ?systemicBlockers,
        'portfolio_adjustments': ?portfolioAdjustments,
        'next_cycle_recommendations': ?nextCycleRecommendations,
        'celebration_title': ?celebrationTitle,
        'milestones_achieved': ?milestonesAchieved,
        'top_performers_recognized': ?topPerformersRecognized,
        'rewards_or_rituals': ?rewardsOrRituals,
        'reflection_notes': ?reflectionNotes,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>?> getWeek13Review(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/week13/review?workspace_id=$workspaceId',
      );
      return _decode(response);
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> getWeek13Celebration(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/week13/celebration?workspace_id=$workspaceId',
      );
      return _decode(response);
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>> getWeek13Readiness(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get(
      '/execution/twelve-week-cycles/$cycleId/week13/readiness?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Portfolio Intelligence & Shared PESTEL (Sprint 6)
  // ====================================================================

  Future<Map<String, dynamic>> detectPortfolioNecessity() async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/portfolios/detect?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolios() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'portfolios');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createPortfolio({
    required String name,
    String? description,
    String? strategicFocus,
    String? brainId,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios?workspace_id=$workspaceId',
      body: {
        'name': name,
        'description': ?description,
        'strategic_focus': ?strategicFocus,
        'brain_id': ?brainId,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioProjects(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/projects?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'projects');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> addProjectToPortfolio(
    String portfolioId, {
    required String projectId,
    String strategicPriority = 'core',
    double capacityAllocation = 0.0,
    double founderAttentionHours = 0.0,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/projects?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'strategic_priority': strategicPriority,
        'capacity_allocation': capacityAllocation,
        'founder_attention_hours': founderAttentionHours,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> removeProjectFromPortfolio(String portfolioId, String projectId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete(
      '/strategy/portfolios/$portfolioId/projects/$projectId?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioPestel(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/pestel?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'pestel_items');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> addPortfolioPestelItem(
    String portfolioId, {
    required String factor,
    required String statement,
    String impact = 'medium',
    String horizon = 'medium',
    String confidence = 'medium',
    String evidenceStatus = 'hypothesis',
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/pestel?workspace_id=$workspaceId',
      body: {
        'factor': factor,
        'statement': statement,
        'impact': impact,
        'horizon': horizon,
        'confidence': confidence,
        'evidence_status': evidenceStatus,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> getPortfolioImpactMatrix(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/portfolios/$portfolioId/impact-matrix?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> setProjectPestelImpact(
    String projectId, {
    required String pestelItemId,
    String impactType = 'POSITIVE',
    String impactMagnitude = 'MEDIUM',
    String? impactAnalysis,
    String? mitigationOrLeverage,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/pestel-impacts?workspace_id=$workspaceId',
      body: {
        'pestel_item_id': pestelItemId,
        'impact_type': impactType,
        'impact_magnitude': impactMagnitude,
        'impact_analysis': ?impactAnalysis,
        'mitigation_or_leverage': ?mitigationOrLeverage,
      },
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Portfolio SWOT, Options & Synergies (Sprint 7)
  // ====================================================================

  Future<List<dynamic>> getPortfolioSwot(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/swot?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'swot_items');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> addPortfolioSwotItem(
    String portfolioId, {
    required String category,
    required String statement,
    String impact = 'medium',
    String likelihood = 'medium',
    String confidence = 'medium',
    String evidenceStatus = 'hypothesis',
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/swot?workspace_id=$workspaceId',
      body: {
        'category': category,
        'statement': statement,
        'impact': impact,
        'likelihood': likelihood,
        'confidence': confidence,
        'evidence_status': evidenceStatus,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioTows(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/tows?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'tows_options');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> addPortfolioTowsOption(
    String portfolioId, {
    required String quadrant,
    required String title,
    String tradeoffs = '',
    String expectedImpact = 'medium',
    String confidence = 'medium',
    String status = 'draft',
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/tows?workspace_id=$workspaceId',
      body: {
        'quadrant': quadrant,
        'title': title,
        'tradeoffs': tradeoffs,
        'expected_impact': expectedImpact,
        'confidence': confidence,
        'status': status,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioSynergies(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/synergies?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'synergies');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> addPortfolioSynergy(
    String portfolioId, {
    required String sourceProjectId,
    required String targetProjectId,
    String synergyType = 'SHARED_CAPABILITY',
    required String description,
    double? estimatedValue,
    String status = 'identified',
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/synergies?workspace_id=$workspaceId',
      body: {
        'source_project_id': sourceProjectId,
        'target_project_id': targetProjectId,
        'synergy_type': synergyType,
        'description': description,
        'estimated_value': ?estimatedValue,
        'status': status,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> deletePortfolioSynergy(String portfolioId, String synergyId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete(
      '/strategy/portfolios/$portfolioId/synergies/$synergyId?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioDependencies(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/dependencies?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'dependencies');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> addPortfolioDependency(
    String portfolioId, {
    required String predecessorProjectId,
    required String successorProjectId,
    String dependencyType = 'BLOCKS',
    String? description,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/dependencies?workspace_id=$workspaceId',
      body: {
        'predecessor_project_id': predecessorProjectId,
        'successor_project_id': successorProjectId,
        'dependency_type': dependencyType,
        'description': ?description,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> deletePortfolioDependency(String portfolioId, String dependencyId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.delete(
      '/strategy/portfolios/$portfolioId/dependencies/$dependencyId?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioOptions(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/options?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'options');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createPortfolioOption(
    String portfolioId, {
    required String title,
    String? description,
    String? towsOptionId,
    double strategicFitScore = 0.8,
    double feasibilityScore = 0.7,
    String riskLevel = 'MEDIUM',
    String status = 'draft',
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/options?workspace_id=$workspaceId',
      body: {
        'title': title,
        'description': ?description,
        'tows_option_id': ?towsOptionId,
        'strategic_fit_score': strategicFitScore,
        'feasibility_score': feasibilityScore,
        'risk_level': riskLevel,
        'status': status,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updatePortfolioOption(
    String portfolioId,
    String optionId, {
    String? status,
    double? strategicFitScore,
    double? feasibilityScore,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/portfolios/$portfolioId/options/$optionId?workspace_id=$workspaceId',
      body: {
        'status': ?status,
        'strategic_fit_score': ?strategicFitScore,
        'feasibility_score': ?feasibilityScore,
      },
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Portfolio Cycles, WIP Limit & Capacity (Sprint 8)
  // ====================================================================

  Future<Map<String, dynamic>> getFounderProfile() async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get('/strategy/founder-profile?workspace_id=$workspaceId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateFounderProfile({
    double? weeklyCapacityHours,
    int? maxActiveStrategicProjects,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/founder-profile?workspace_id=$workspaceId',
      body: {
        'weekly_capacity_hours': ?weeklyCapacityHours,
        'max_active_strategic_projects': ?maxActiveStrategicProjects,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getPortfolioCycles(String portfolioId) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get('/strategy/portfolios/$portfolioId/cycles?workspace_id=$workspaceId');
      return _decodeList(response, 'cycles');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> createPortfolioCycle(
    String portfolioId, {
    required String title,
    String? startDate,
    String? endDate,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/cycles?workspace_id=$workspaceId',
      body: {
        'title': title,
        'start_date': ?startDate,
        'end_date': ?endDate,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> activatePortfolioCycle(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolio-cycles/$cycleId/activate?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> getCycleAllocations(String cycleId) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/portfolio-cycles/$cycleId/allocations?workspace_id=$workspaceId',
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> setCapacityAllocation(
    String cycleId, {
    required String projectId,
    required double allocatedPercentage,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolio-cycles/$cycleId/allocations/capacity?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'allocated_percentage': allocatedPercentage,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> setFounderAttentionAllocation(
    String cycleId, {
    required String projectId,
    required double allocatedHoursPerWeek,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolio-cycles/$cycleId/allocations/founder-attention?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'allocated_hours_per_week': allocatedHoursPerWeek,
      },
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Next Best Action Engine (Sprint 9 Spec §37 & V12.6)
  // ====================================================================

  Future<List<dynamic>> getCeoNextActions({int limit = 5}) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/ceo/next-actions?workspace_id=$workspaceId&limit=$limit',
      );
      return _decodeList(response, 'next_actions');
    } catch (_) {
      return [];
    }
  }

  Future<List<dynamic>> evaluateCeoNextActions({
    String? projectId,
    String? portfolioId,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/ceo/next-actions/evaluate?workspace_id=$workspaceId',
      body: {
        'project_id': ?projectId,
        'portfolio_id': ?portfolioId,
      },
    );
    return _decodeList(response, 'rankings');
  }

  Future<Map<String, dynamic>> updateNextActionStatus(
    String actionId,
    String status,
  ) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/ceo/next-actions/$actionId/status?workspace_id=$workspaceId',
      body: {'status': status},
    );
    return _decode(response);
  }

  // ====================================================================
  // mCOSA V12 Sprint 10 — Living PESTEL & Model Profiles (Spec §48, §56)
  // ====================================================================

  Future<List<dynamic>> getPestelSignals() async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/pestel-signals?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'signals');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> ingestPestelSignal({
    required String signalTitle,
    required String pestelCategory,
    required String magnitude,
    String? signalSummary,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/pestel-signals?workspace_id=$workspaceId',
      body: {
        'signal_title': signalTitle,
        'pestel_category': pestelCategory,
        'magnitude': magnitude,
        'signal_summary': ?signalSummary,
      },
    );
    return _decode(response);
  }

  Future<List<dynamic>> getModelRunsAudit({int limit = 20}) async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/model-runs/audit?workspace_id=$workspaceId&limit=$limit',
      );
      return _decodeList(response, 'audits');
    } catch (_) {
      return [];
    }
  }

  Future<List<dynamic>> getModelProfiles() async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/model-profiles?workspace_id=$workspaceId',
      );
      return _decodeList(response, 'profiles');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> updateModelProfile(
    String profileId, {
    String? displayName,
    double? temperature,
    bool? isActive,
  }) async {
    final workspaceId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/model-profiles/$profileId?workspace_id=$workspaceId',
      body: {
        'display_name': ?displayName,
        'temperature': ?temperature,
        'is_active': ?isActive,
      },
    );
    return _decode(response);
  }
}








