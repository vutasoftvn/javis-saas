import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// Strategic Projects, Initiatives, Methodology & MVP Roadmap
class ProjectService extends StrategyServiceBase {
  // ====================================================================
  // Strategic Projects & Initiatives
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getProjects() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/operations/projects?workspace_id=$workspaceId');
      return decodeList(response, 'projects');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createProject({
    required String title,
    String? description,
    String? phase,
    String? projectStage,
    String? stageGoal,
    String? currentGate,
    String? status,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/operations/projects?workspace_id=$workspaceId',
      body: {
        'title': title,
        'description': ?description,
        'lifecycleStage': ?(projectStage ?? phase),
        'phase': ?phase,
        'project_stage': ?projectStage,
        'stage_goal': ?stageGoal,
        'current_gate': ?currentGate,
        'status': ?status,
        'startDate': startDate?.toIso8601String(),
        'endDate': endDate?.toIso8601String(),
        'start_date': startDate?.toIso8601String(),
        'end_date': endDate?.toIso8601String(),
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateProject(
    String projectId, {
    String? title,
    String? phase,
    String? currentGate,
    String? status,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/operations/projects/$projectId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'lifecycleStage': ?phase,
        'phase': ?phase,
        'current_gate': ?currentGate,
        'status': ?status,
        'startDate': startDate?.toIso8601String(),
        'endDate': endDate?.toIso8601String(),
        'start_date': startDate?.toIso8601String(),
        'end_date': endDate?.toIso8601String(),
      },
    );
    return decode(response);
  }

  Future<void> deleteProject(String projectId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/operations/projects/$projectId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getInitiatives({String? projectId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final query = projectId != null ? 'workspace_id=$workspaceId&project_id=$projectId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/strategy/initiatives?$query');
      return decodeList(response, 'initiatives');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createInitiative({
    required String title,
    String? projectId,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/initiatives?workspace_id=$workspaceId',
      body: {
        'title': title,
        'project_id': ?projectId,
        'status': ?status,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateInitiative(
    String initiativeId, {
    String? title,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/initiatives/$initiativeId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'status': ?status,
      },
    );
    return decode(response);
  }

  Future<void> deleteInitiative(String initiativeId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/initiatives/$initiativeId?workspace_id=$workspaceId');
    decode(response);
  }

  // ====================================================================
  // mCOSA V12 Single Project Journey & Assisted Terra
  // ====================================================================

  Future<Map<String, dynamic>> classifyProject(
    String projectId, {
    String? titleOverride,
    String? descriptionOverride,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/classify?workspace_id=$workspaceId',
      body: {
        'title_override': ?titleOverride,
        'description_override': ?descriptionOverride,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getMethodologyPlan(String projectId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/projects/$projectId/methodology?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> routeMethodology(
    String projectId, {
    List<String>? customMethodologies,
    String? rationaleOverride,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/methodology?workspace_id=$workspaceId',
      body: {
        'custom_methodologies': ?customMethodologies,
        'rationale_override': ?rationaleOverride,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> exportAnalysisPrompt({
    String? projectId,
    String? canvasId,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analysis/export?workspace_id=$workspaceId',
      body: {
        'project_id': ?projectId,
        'canvas_id': ?canvasId,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> importAnalysisResult(
    String rawInput, {
    String? projectId,
    String? canvasId,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/analysis/import?workspace_id=$workspaceId',
      body: {
        'raw_input': rawInput,
        'project_id': ?projectId,
        'canvas_id': ?canvasId,
      },
    );
    return decode(response);
  }

  // ====================================================================
  // SaaS Project Stage & Agent Orchestration
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getWorkspaceTemplates() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/strategy/workspace-templates?workspace_id=$workspaceId');
      return decodeList(response, 'templates');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<StrategyListResult<Map<String, dynamic>>> provisionWorkspaceTemplates() async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.post('/strategy/workspace-templates:provision?workspace_id=$workspaceId');
      return decodeList(response, 'templates');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> resetWorkspaceTemplate(String templateId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/workspace-templates/$templateId:reset?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> updateWorkspaceTemplate(String templateId, {String? name, List<dynamic>? capabilities}) async {
    final workspaceId = await requireWorkspaceId();
    final body = <String, dynamic>{};
    if (name != null) body['name'] = name;
    if (capabilities != null) body['capabilities'] = capabilities;
    final response = await ApiClient.put('/strategy/workspace-templates/$templateId?workspace_id=$workspaceId', body: body);
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getProjectStages(String projectId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get('/strategy/projects/$projectId/stages?workspace_id=$workspaceId');
      return decodeList(response, 'stages');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> generateMvpRoadmap(String projectId, {String? instruction}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/mvp-roadmap:generate?workspace_id=$workspaceId',
      body: instruction != null && instruction.trim().isNotEmpty ? {'instruction': instruction.trim()} : null,
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> saveMvpRoadmapDraft(String projectId, List<Map<String, dynamic>> stages) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/projects/$projectId/mvp-roadmap?workspace_id=$workspaceId',
      body: {'stages': stages},
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> confirmMvpRoadmap(String projectId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/projects/$projectId/mvp-roadmap:confirm?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> planMvpStage(String projectId, String stageId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/stages/$stageId:plan?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> activateMvpStage(
    String projectId,
    String stageId, {
    required List<Map<String, dynamic>> objectives,
    required List<String> weeklyFocus,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/projects/$projectId/stages/$stageId:activate?workspace_id=$workspaceId',
      body: {'objectives': objectives, 'weekly_focus': weeklyFocus},
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> generateStageServiceAssessment(String projectId, String stageId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.post(
        '/strategy/projects/$projectId/stages/$stageId/service-assessment:generate?workspace_id=$workspaceId',
      );
      return decodeList(response, 'assessments');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<StrategyListResult<Map<String, dynamic>>> confirmStageServiceAssessment(
    String projectId,
    String stageId,
    List<Map<String, dynamic>> decisions,
  ) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.post(
        '/strategy/projects/$projectId/stages/$stageId/service-assessment:confirm?workspace_id=$workspaceId',
        body: {'decisions': decisions},
      );
      return decodeList(response, 'assessments');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> previewStageRevision(
    String stageId, {
    String? hypothesis,
    List<String>? scope,
    List<String>? nonGoals,
    List<String>? exitCriteria,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/stages/$stageId:preview-revision?workspace_id=$workspaceId',
      body: {
        'hypothesis': ?hypothesis,
        'scope': ?scope,
        'non_goals': ?nonGoals,
        'exit_criteria': ?exitCriteria,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> applyStageRevision(String stageId, String revisionId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/stages/$stageId:apply-revision?workspace_id=$workspaceId',
      body: {'revision_id': revisionId},
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> generateWeek13(String stageId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/stages/$stageId/week-13:generate?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> confirmWeek13(String stageId, String decision, String rationale) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/stages/$stageId/week-13:confirm?workspace_id=$workspaceId',
      body: {'decision': decision, 'rationale': rationale},
    );
    return decode(response);
  }
}
