import 'package:get/get.dart';
import '../../../data/services/strategy_service.dart';

/// Điều phối luồng founder kickoff: brief -> MVP roadmap -> activate stage ->
/// service assessment -> Week 13 gate (SaaS Project Stage & Agent
/// Orchestration design). Roadmap nháp do AI sinh ra không được lưu ở backend
/// cho tới khi gọi saveRoadmapDraft/confirmRoadmap - controller phản ánh đúng
/// điều đó bằng cách giữ [roadmapDraft] tách biệt khỏi [stages]/[activeStage].
class ProjectOrchestrationController extends GetxController {
  final StrategyService _service;
  ProjectOrchestrationController({StrategyService? service}) : _service = service ?? StrategyService();

  final isLoading = false.obs;
  final isGeneratingRoadmap = false.obs;
  final isSaving = false.obs;
  final errorMessage = RxnString();

  /// Project đang được AI sinh roadmap (dùng để hiển thị loading trên card).
  final activeProjectId = ''.obs;


  /// AI-proposed roadmap, never persisted until saveRoadmapDraft/confirmRoadmap.
  final Rxn<Map<String, dynamic>> roadmapDraft = Rxn<Map<String, dynamic>>();

  /// Persisted MvpStage rows for the current project (DRAFT/CONFIRMED/ACTIVE/...).
  final RxList<dynamic> stages = <dynamic>[].obs;

  /// The one ACTIVE stage, if any - null until activateStage succeeds.
  final Rxn<Map<String, dynamic>> activeStage = Rxn<Map<String, dynamic>>();

  final Rxn<Map<String, dynamic>> stagePlanDraft = Rxn<Map<String, dynamic>>();
  final RxList<dynamic> serviceAssessments = <dynamic>[].obs;
  final Rxn<Map<String, dynamic>> revisionPreview = Rxn<Map<String, dynamic>>();
  final Rxn<Map<String, dynamic>> week13Result = Rxn<Map<String, dynamic>>();

  final RxList<dynamic> workspaceTemplates = <dynamic>[].obs;

  Future<void> _runGuarded(Future<void> Function() action) async {
    errorMessage.value = null;
    try {
      await action();
    } on StrategyApiException catch (e) {
      errorMessage.value = e.message;
    } catch (e) {
      errorMessage.value = 'Có lỗi xảy ra: $e';
    }
  }

  Future<void> generateRoadmap(String projectId) async {
    isGeneratingRoadmap.value = true;
    await _runGuarded(() async {
      final draft = await _service.generateMvpRoadmap(projectId);
      roadmapDraft.value = draft;
    });
    isGeneratingRoadmap.value = false;
  }

  void clearRoadmapDraft() => roadmapDraft.value = null;

  Future<void> saveRoadmapDraft(String projectId, List<Map<String, dynamic>> editedStages) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final result = await _service.saveMvpRoadmapDraft(projectId, editedStages);
      stages.value = (result['stages'] as List<dynamic>?) ?? [];
    });
    isSaving.value = false;
  }

  Future<void> confirmRoadmap(String projectId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final result = await _service.confirmMvpRoadmap(projectId);
      stages.value = (result['stages'] as List<dynamic>?) ?? [];
      roadmapDraft.value = null;
    });
    isSaving.value = false;
  }

  Future<void> planStage(String projectId, String stageId) async {
    isLoading.value = true;
    await _runGuarded(() async {
      stagePlanDraft.value = await _service.planMvpStage(projectId, stageId);
    });
    isLoading.value = false;
  }

  Future<void> activateStage(String projectId, String stageId) async {
    final plan = stagePlanDraft.value;
    if (plan == null) {
      errorMessage.value = 'Chưa có kế hoạch được duyệt cho stage này';
      return;
    }
    isSaving.value = true;
    await _runGuarded(() async {
      final result = await _service.activateMvpStage(
        projectId, stageId,
        objectives: List<Map<String, dynamic>>.from(plan['objectives'] as List),
        weeklyFocus: List<String>.from(plan['weekly_focus'] as List),
      );
      final updated = Map<String, dynamic>.from(result['stage'] as Map);
      activeStage.value = updated;
      final index = stages.indexWhere((s) => s['id'] == updated['id']);
      if (index >= 0) {
        stages[index] = updated;
      } else {
        stages.add(updated);
      }
    });
    isSaving.value = false;
  }

  Future<void> generateServiceAssessment(String projectId, String stageId) async {
    isLoading.value = true;
    await _runGuarded(() async {
      serviceAssessments.value = await _service.generateStageServiceAssessment(projectId, stageId);
    });
    isLoading.value = false;
  }

  Future<void> confirmServiceAssessment(
    String projectId,
    String stageId,
    List<Map<String, dynamic>> decisions,
  ) async {
    isSaving.value = true;
    await _runGuarded(() async {
      serviceAssessments.value = await _service.confirmStageServiceAssessment(projectId, stageId, decisions);
    });
    isSaving.value = false;
  }

  Future<void> previewRevision(
    String stageId, {
    String? hypothesis,
    List<String>? scope,
    List<String>? nonGoals,
    List<String>? exitCriteria,
  }) async {
    isLoading.value = true;
    await _runGuarded(() async {
      revisionPreview.value = await _service.previewStageRevision(
        stageId, hypothesis: hypothesis, scope: scope, nonGoals: nonGoals, exitCriteria: exitCriteria,
      );
    });
    isLoading.value = false;
  }

  Future<void> applyRevision(String stageId) async {
    final revision = revisionPreview.value;
    if (revision == null) return;
    isSaving.value = true;
    await _runGuarded(() async {
      final updated = await _service.applyStageRevision(stageId, revision['id'] as String);
      activeStage.value = updated;
      revisionPreview.value = null;
      final index = stages.indexWhere((s) => s['id'] == updated['id']);
      if (index >= 0) stages[index] = updated;
    });
    isSaving.value = false;
  }

  Future<void> generateWeek13(String stageId) async {
    isLoading.value = true;
    await _runGuarded(() async {
      week13Result.value = await _service.generateWeek13(stageId);
    });
    isLoading.value = false;
  }

  Future<void> confirmWeek13Decision(String stageId, String decision, String rationale) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final result = await _service.confirmWeek13(stageId, decision, rationale);
      final updated = Map<String, dynamic>.from(result['stage'] as Map);
      final index = stages.indexWhere((s) => s['id'] == updated['id']);
      if (index >= 0) stages[index] = updated;
      if (updated['status'] != 'ACTIVE') activeStage.value = null;
      week13Result.value = null;
    });
    isSaving.value = false;
  }

  Future<void> loadWorkspaceTemplates() async {
    isLoading.value = true;
    await _runGuarded(() async {
      workspaceTemplates.value = await _service.getWorkspaceTemplates();
    });
    isLoading.value = false;
  }

  Future<void> provisionWorkspaceTemplates() async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _service.provisionWorkspaceTemplates();
      await loadWorkspaceTemplates();
    });
    isSaving.value = false;
  }

  Future<void> resetWorkspaceTemplate(String templateId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _service.resetWorkspaceTemplate(templateId);
      await loadWorkspaceTemplates();
    });
    isSaving.value = false;
  }
}
