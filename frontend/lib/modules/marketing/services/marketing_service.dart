import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../../data/models/commercial_models.dart';

/// Lỗi từ Marketing API (401 chưa đăng nhập, 404 sai workspace/brain, 409 duyệt trùng...)
class MarketingApiException implements Exception {
  final int statusCode;
  final String message;
  MarketingApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

/// Client cho `/api/v1/marketing`.
///
/// Backend bắt buộc token + `workspace_id` trên mọi endpoint (tenancy server-side), nên
/// service không được nuốt lỗi: nếu thiếu workspace hoặc gọi thất bại thì ném lỗi để
/// controller hiển thị đúng nguyên nhân, thay vì trả danh sách rỗng khiến UI trông như
/// "chưa có dữ liệu".
class MarketingService {
  Future<String> _requireWorkspaceId() async {
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId == null || workspaceId.isEmpty) {
      throw MarketingApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

  Future<String> _query(String brainId, [Map<String, String> extra = const {}]) async {
    final workspaceId = await _requireWorkspaceId();
    final params = <String>['workspace_id=$workspaceId'];
    if (brainId.isNotEmpty) {
      params.add('brain_id=$brainId');
    }
    extra.forEach((key, value) => params.add('$key=${Uri.encodeQueryComponent(value)}'));
    return '?${params.join('&')}';
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
      // giữ nguyên thông báo mặc định nếu body không phải JSON
    }
    throw MarketingApiException(response.statusCode, detail);
  }

  List<dynamic> _list(dynamic data, String key) {
    if (data is Map && data[key] is List) return data[key] as List<dynamic>;
    return const [];
  }

  Map<String, dynamic> _map(dynamic data, String key) {
    if (data is Map && data[key] is Map) return Map<String, dynamic>.from(data[key] as Map);
    return <String, dynamic>{};
  }

  // ====================================================================
  // Projects
  // ====================================================================

  Future<List<dynamic>> getProjects() async {
    final workspaceId = await _requireWorkspaceId();
    try {
      final response = await ApiClient.get('/strategy/projects?workspace_id=$workspaceId');
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(response.body);
        return data is Map && data['projects'] is List ? (data['projects'] as List<dynamic>) : [];
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  // ====================================================================
  // Cockpit & Analytics
  // ====================================================================

  Future<Map<String, dynamic>> getCockpitSummary(String brainId, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/cockpit-summary${await _query(brainId, extra)}');
    return _map(_decode(response), 'summary');
  }

  Future<Map<String, dynamic>> getAnalyticsOverview(String brainId, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/analytics/overview${await _query(brainId, extra)}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> getFunnel(String brainId, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/funnel${await _query(brainId, extra)}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  // ====================================================================
  // Marketing Context
  // ====================================================================

  Future<Map<String, dynamic>?> getMarketingContext(String brainId, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/context${await _query(brainId, extra)}');
    final data = _decode(response);
    if (data is Map && data['marketing_context'] is Map) {
      return Map<String, dynamic>.from(data['marketing_context'] as Map);
    }
    if (data is Map && data['context'] is Map) {
      return Map<String, dynamic>.from(data['context'] as Map);
    }
    return null;
  }

  Future<Map<String, dynamic>> updateMarketingContext(String brainId, Map<String, dynamic> payload, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.post('/marketing/context${await _query(brainId, extra)}', body: payload);
    return _map(_decode(response), 'marketing_context');
  }

  // ====================================================================
  // Objectives
  // ====================================================================

  Future<List<dynamic>> getMarketingObjectives(String brainId, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/objectives${await _query(brainId, extra)}');
    return _list(_decode(response), 'objectives');
  }

  Future<Map<String, dynamic>> createMarketingObjective(String brainId, Map<String, dynamic> payload, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.post('/marketing/objectives${await _query(brainId, extra)}', body: payload);
    return _map(_decode(response), 'objective');
  }

  Future<Map<String, dynamic>> updateMarketingObjective(String objectiveId, Map<String, dynamic> payload) async {
    final response = await ApiClient.patch('/marketing/objectives/$objectiveId${await _query('')}', body: payload);
    return _map(_decode(response), 'objective');
  }

  Future<void> deleteMarketingObjective(String objectiveId) async {
    final response = await ApiClient.delete('/marketing/objectives/$objectiveId${await _query('')}');
    _decode(response);
  }

  // ====================================================================
  // Campaigns
  // ====================================================================

  Future<List<CampaignModel>> getTypedCampaigns(String brainId, {String? projectId}) async {
    final list = await getCampaigns(brainId, projectId: projectId);
    return list.map((e) => CampaignModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<List<dynamic>> getCampaigns(String brainId, {String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/campaigns${await _query(brainId, extra)}');
    return _list(_decode(response), 'campaigns');
  }

  Future<Map<String, dynamic>> createCampaign(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/campaigns${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'campaign');
  }

  Future<Map<String, dynamic>> getCampaignDetail(String campaignId) async {
    final response = await ApiClient.get('/marketing/campaigns/$campaignId${await _query('')}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> updateCampaign(String campaignId, Map<String, dynamic> payload) async {
    final response = await ApiClient.patch('/marketing/campaigns/$campaignId${await _query('')}', body: payload);
    return _map(_decode(response), 'campaign');
  }

  /// Đổi trạng thái chiến dịch. Với `active`/`paused` backend trả về
  /// `status == 'pending_approval'` vì thay đổi phải qua người duyệt.
  Future<Map<String, dynamic>> changeCampaignStatus(String campaignId, String status) async {
    final response = await ApiClient.post(
      '/marketing/campaigns/$campaignId/status${await _query('')}',
      body: {'status': status},
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<void> deleteCampaign(String campaignId) async {
    final response = await ApiClient.delete('/marketing/campaigns/$campaignId${await _query('')}');
    _decode(response);
  }

  Future<Map<String, dynamic>> createCampaignAsset(String campaignId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post(
      '/marketing/campaigns/$campaignId/assets${await _query('')}',
      body: payload,
    );
    return _map(_decode(response), 'asset');
  }

  Future<Map<String, dynamic>> requestAssetApproval(String assetId) async {
    final response = await ApiClient.post('/marketing/assets/$assetId/request-approval${await _query('')}');
    return _map(_decode(response), 'approval');
  }

  // ====================================================================
  // Experiments
  // ====================================================================

  Future<List<dynamic>> getExperiments(String brainId) async {
    final response = await ApiClient.get('/marketing/experiments${await _query(brainId)}');
    return _list(_decode(response), 'experiments');
  }

  Future<Map<String, dynamic>> createExperiment(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/experiments${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'experiment');
  }

  Future<Map<String, dynamic>> evaluateExperiment(String experimentId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post(
      '/marketing/experiments/$experimentId/evaluate${await _query('')}',
      body: payload,
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> decideExperiment(String experimentId, String decision, String? learning) async {
    final response = await ApiClient.post(
      '/marketing/experiments/$experimentId/decide${await _query('')}',
      body: {'decision': decision, 'learning': learning},
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  // ====================================================================
  // Learnings & Metrics
  // ====================================================================

  Future<Map<String, dynamic>> getLearnings(String brainId) async {
    final response = await ApiClient.get('/marketing/learnings${await _query(brainId)}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> createLearning(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/learnings${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'learning');
  }

  Future<List<dynamic>> getMetrics(String brainId) async {
    final response = await ApiClient.get('/marketing/metrics${await _query(brainId)}');
    return _list(_decode(response), 'metrics');
  }

  Future<Map<String, dynamic>> upsertMetric(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/metrics${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'metric');
  }

  Future<List<dynamic>> getMetricHistory(String metricName) async {
    final response = await ApiClient.get('/marketing/metrics/$metricName/history${await _query('')}');
    return _list(_decode(response), 'points');
  }

  // ====================================================================
  // Skill Registry & Approvals
  // ====================================================================

  Future<List<dynamic>> getSkills() async {
    final response = await ApiClient.get('/marketing/skills${await _query('')}');
    return _list(_decode(response), 'skills');
  }

  Future<List<dynamic>> getSkillExecutions(String brainId) async {
    final response = await ApiClient.get('/marketing/skill-executions${await _query(brainId)}');
    return _list(_decode(response), 'executions');
  }

  Future<Map<String, dynamic>> executeSkill(String brainId, String capabilityId, Map<String, dynamic> taskInput) async {
    final response = await ApiClient.post(
      '/marketing/execute-skill${await _query(brainId)}',
      body: {
        'capability_id': capabilityId,
        'task_input': taskInput,
        'requested_by_agent': 'Marketing Director',
      },
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<List<dynamic>> getApprovals(String brainId, {String status = 'pending'}) async {
    final response = await ApiClient.get(
      '/marketing/approvals${await _query(brainId, {'status': status})}',
    );
    return _list(_decode(response), 'approvals');
  }

  Future<Map<String, dynamic>> reviewApproval(String approvalId, bool approved, String? notes) async {
    final response = await ApiClient.post(
      '/marketing/approvals/$approvalId/review${await _query('')}',
      body: {'approved': approved, 'review_notes': notes},
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  // ====================================================================
  // Canvas Sub-sections: Research, Product Marketing, Offers, 12W Plan
  // ====================================================================

  Future<Map<String, dynamic>> getCustomerResearch(String brainId) async {
    final response = await ApiClient.get('/marketing/context/customer-research${await _query(brainId)}');
    return _map(_decode(response), 'customer_research');
  }

  Future<Map<String, dynamic>> updateCustomerResearch(String brainId, Map<String, dynamic> research) async {
    final response = await ApiClient.patch(
      '/marketing/context/customer-research${await _query(brainId)}',
      body: {'customer_research': research},
    );
    return _map(_decode(response), 'customer_research');
  }

  Future<Map<String, dynamic>> getProductMarketing(String brainId) async {
    final response = await ApiClient.get('/marketing/context/product-marketing${await _query(brainId)}');
    return _map(_decode(response), 'product_marketing');
  }

  Future<Map<String, dynamic>> updateProductMarketing(String brainId, Map<String, dynamic> pm) async {
    final response = await ApiClient.patch(
      '/marketing/context/product-marketing${await _query(brainId)}',
      body: {'product_marketing': pm},
    );
    return _map(_decode(response), 'product_marketing');
  }

  Future<Map<String, dynamic>> getOfferArchitecture(String brainId) async {
    final response = await ApiClient.get('/marketing/context/offer-architecture${await _query(brainId)}');
    return _map(_decode(response), 'offer_architecture');
  }

  Future<Map<String, dynamic>> updateOfferArchitecture(String brainId, Map<String, dynamic> offer) async {
    final response = await ApiClient.patch(
      '/marketing/context/offer-architecture${await _query(brainId)}',
      body: {'offer_architecture': offer},
    );
    return _map(_decode(response), 'offer_architecture');
  }

  Future<Map<String, dynamic>> get12WPlan(String brainId) async {
    final response = await ApiClient.get('/marketing/context/12w-plan${await _query(brainId)}');
    return _map(_decode(response), 'marketing_plan_12w');
  }

  Future<Map<String, dynamic>> update12WPlan(String brainId, Map<String, dynamic> plan) async {
    final response = await ApiClient.patch(
      '/marketing/context/12w-plan${await _query(brainId)}',
      body: {'marketing_plan_12w': plan},
    );
    return _map(_decode(response), 'marketing_plan_12w');
  }

  // ====================================================================
  // Marketing Loops (§18)
  // ====================================================================

  Future<List<dynamic>> getLoops(String brainId) async {
    final response = await ApiClient.get('/marketing/loops${await _query(brainId)}');
    return _list(_decode(response), 'loops');
  }

  Future<Map<String, dynamic>> createLoop(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/loops${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'loop');
  }

  Future<Map<String, dynamic>> updateLoop(String loopId, Map<String, dynamic> payload) async {
    final response = await ApiClient.patch('/marketing/loops/$loopId${await _query('')}', body: payload);
    return _map(_decode(response), 'loop');
  }

  Future<void> deleteLoop(String loopId) async {
    final response = await ApiClient.delete('/marketing/loops/$loopId${await _query('')}');
    _decode(response);
  }

  Future<Map<String, dynamic>> triggerLoop(String loopId) async {
    final response = await ApiClient.post('/marketing/loops/$loopId/trigger${await _query('')}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  // ====================================================================
  // Attribution Analytics (§28)
  // ====================================================================

  Future<Map<String, dynamic>> calculateAttribution(Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/analytics/attribution${await _query('')}', body: payload);
    return _map(_decode(response), 'attribution');
  }

  // ====================================================================
  // Decision Journal (§53)
  // ====================================================================

  Future<List<dynamic>> getDecisions(String brainId) async {
    final response = await ApiClient.get('/marketing/decisions${await _query(brainId)}');
    return _list(_decode(response), 'decisions');
  }

  Future<Map<String, dynamic>> createDecision(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/decisions${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'decision');
  }

  Future<Map<String, dynamic>> updateDecision(String decisionId, Map<String, dynamic> payload) async {
    final response = await ApiClient.patch('/marketing/decisions/$decisionId${await _query('')}', body: payload);
    return _map(_decode(response), 'decision');
  }

  Future<void> deleteDecision(String decisionId) async {
    final response = await ApiClient.delete('/marketing/decisions/$decisionId${await _query('')}');
    _decode(response);
  }

  // ====================================================================
  // Recommendations (§52)
  // ====================================================================

  Future<List<dynamic>> getRecommendations(String brainId, {String? status}) async {
    final extra = status != null ? {'status': status} : const <String, String>{};
    final response = await ApiClient.get('/marketing/recommendations${await _query(brainId, extra)}');
    return _list(_decode(response), 'recommendations');
  }

  Future<Map<String, dynamic>> createRecommendation(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/recommendations${await _query(brainId)}', body: payload);
    return _map(_decode(response), 'recommendation');
  }

  Future<Map<String, dynamic>> updateRecommendationStatus(String recId, String status) async {
    final response = await ApiClient.post(
      '/marketing/recommendations/$recId/status${await _query('')}',
      body: {'status': status},
    );
    return _map(_decode(response), 'recommendation');
  }

  // ====================================================================
  // Market Validation Engine (E3.md §16 - §48)
  // ====================================================================

  Future<List<dynamic>> getAssumptions({
    String? projectId,
    String? category,
    String? status,
    int? minCriticality,
  }) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    if (category != null && category.isNotEmpty) extra['category'] = category;
    if (status != null && status.isNotEmpty) extra['status'] = status;
    if (minCriticality != null) extra['min_criticality'] = minCriticality.toString();

    final response = await ApiClient.get('/marketing/assumptions${await _query('', extra)}');
    final data = _decode(response);
    return data is List ? data : [];
  }

  Future<Map<String, dynamic>> getAssumptionsSummary({String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/assumptions/summary${await _query('', extra)}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> createAssumption(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/assumptions${await _query(brainId)}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> updateAssumption(String id, Map<String, dynamic> payload) async {
    final response = await ApiClient.patch('/marketing/assumptions/$id${await _query('')}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<void> deleteAssumption(String id) async {
    final response = await ApiClient.delete('/marketing/assumptions/$id${await _query('')}');
    _decode(response);
  }

  Future<List<dynamic>> getEvidenceList({String? projectId, String? assumptionId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    if (assumptionId != null && assumptionId.isNotEmpty) extra['assumption_id'] = assumptionId;
    final response = await ApiClient.get('/marketing/evidence${await _query('', extra)}');
    final data = _decode(response);
    return data is List ? data : [];
  }

  Future<Map<String, dynamic>> createEvidence(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/evidence${await _query(brainId)}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> extractAssumptionsAI(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/ai/extract-assumptions${await _query(brainId)}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> getCanvasesStatus({String? projectId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    final response = await ApiClient.get('/marketing/canvases/status${await _query('', extra)}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> designExperimentAI(Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/ai/design-experiment${await _query('')}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> checkScaleWarning(String assumptionId) async {
    final response = await ApiClient.post(
      '/marketing/scale-warning-check${await _query('')}',
      body: {'assumption_id': int.tryParse(assumptionId) ?? assumptionId},
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> completeValidationExperiment(String experimentId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post(
      '/marketing/experiments/$experimentId/complete${await _query('')}',
      body: payload,
    );
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> extractInterviewAI(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/ai/extract-interview${await _query(brainId)}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> recordCustomerInterview(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/crm/interviews${await _query(brainId)}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<List<dynamic>> getCustomerInterviews({String? projectId, String? contactId}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    if (contactId != null && contactId.isNotEmpty) extra['contact_id'] = contactId;
    final response = await ApiClient.get('/marketing/crm/interviews${await _query('', extra)}');
    final data = _decode(response);
    return data is List ? data : [];
  }

  Future<List<dynamic>> getAttributions({String? experimentId, String? campaignId}) async {
    final extra = <String, String>{};
    if (experimentId != null && experimentId.isNotEmpty) extra['experiment_id'] = experimentId;
    if (campaignId != null && campaignId.isNotEmpty) extra['campaign_id'] = campaignId;
    final response = await ApiClient.get('/marketing/crm/attributions${await _query('', extra)}');
    final data = _decode(response);
    return data is List ? data : [];
  }

  Future<Map<String, dynamic>> evaluateLearningLoopAI(Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/ai/evaluate-learning-loop${await _query('')}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> recordLearningAndDecision(String brainId, Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/learning-loop/decisions${await _query(brainId)}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> proposeCanvasRevisionAI(Map<String, dynamic> payload) async {
    final response = await ApiClient.post('/marketing/ai/propose-canvas-revision${await _query('')}', body: payload);
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<List<dynamic>> getCanvasRevisions({String? projectId, String? canvasType, String? status}) async {
    final extra = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) extra['project_id'] = projectId;
    if (canvasType != null && canvasType.isNotEmpty) extra['canvas_type'] = canvasType;
    if (status != null && status.isNotEmpty) extra['status'] = status;
    final response = await ApiClient.get('/marketing/canvases/revisions${await _query('', extra)}');
    final data = _decode(response);
    return data is List ? data : [];
  }

  Future<Map<String, dynamic>> approveCanvasRevision(String revisionId) async {
    final response = await ApiClient.post('/marketing/canvases/revisions/$revisionId/approve${await _query('')}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }

  Future<Map<String, dynamic>> rejectCanvasRevision(String revisionId) async {
    final response = await ApiClient.post('/marketing/canvases/revisions/$revisionId/reject${await _query('')}');
    final data = _decode(response);
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }
}


