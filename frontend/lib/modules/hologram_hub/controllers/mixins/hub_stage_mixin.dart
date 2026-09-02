import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../../../data/models/stage_model.dart';
import '../../../../modules/strategy/services/stage_service.dart';
import '../../../../modules/strategy/services/strategy_service.dart';

mixin HubStageMixin on GetxController {
  // ── Abstract service getters ─────────────────────────────────────────────
  StageService get stageService;
  StrategyService get strategyService;
  RxnString get dataLoadError;

  // Fix (2026-09-02, epoch-guard siblings) — cùng cơ chế đã áp dụng ở
  // `HubControlPlaneMixin._workspaceGeneration`: các hàm `load*()` dưới đây
  // capture giá trị này NGAY TRƯỚC mỗi `await` gọi service, rồi so sánh lại
  // NGAY SAU khi await resolve — nếu khác, đã có switch workspace hoặc
  // logout xảy ra trong lúc chờ, discard response, không ghi vào Rx state.
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // ── Observables ──────────────────────────────────────────────────────────
  final stageContext = Rxn<StageContextModel>();
  final currentProjectStage = ProjectStage.p1ProblemValidation.obs;
  final projectsList = <Map<String, dynamic>>[].obs;
  final selectedProjectId = Rxn<int>();
  final isStageLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadStageContext({int? projectId}) async {
    final generation = _workspaceGeneration;
    isStageLoading.value = true;
    try {
      final contextData = await stageService.getStageContext(
        projectId: projectId,
      );
      if (_workspaceGeneration != generation) return;
      if (contextData != null) {
        stageContext.value = contextData;
        selectedProjectId.value = contextData.projectId;
        currentProjectStage.value = contextData.projectStage;
        if (contextData.projectId != null) {
          loadEvidenceData(contextData.projectId);
          loadStageLensesData(contextData.projectId);
          loadStageGateData(contextData.projectId);
        }
      }
    } catch (e) {
      debugPrint('Error loading stage context: $e');
    } finally {
      isStageLoading.value = false;
    }
  }

  Future<void> loadProjectsList() async {
    final generation = _workspaceGeneration;
    try {
      final result = await strategyService.getProjects();
      if (_workspaceGeneration != generation) return;
      if (result.errorMessage != null) {
        // Lỗi thật (401/403/409/5xx, mất mạng...) — KHÔNG ghi đè
        // projectsList bằng [] để tránh isGenesisMode hiểu nhầm "chưa có dự
        // án nào" và đẩy người dùng vào lại luồng onboarding dù họ đã có dự
        // án, chỉ là lần tải này thất bại.
        dataLoadError.value = result.errorMessage;
        return;
      }
      // Tải thành công — xoá lỗi cũ (nếu có) để không kẹt trạng thái lỗi
      // vĩnh viễn sau một lần retry thành công.
      dataLoadError.value = null;
      projectsList.value = result.items;
    } catch (e) {
      debugPrint('Error loading projects list: $e');
      if (_workspaceGeneration != generation) return;
      dataLoadError.value = 'Không thể tải danh sách dự án: $e';
    }
  }

  void onProjectSelected(int? projectId) {
    if (projectId != selectedProjectId.value) {
      selectedProjectId.value = projectId;
      loadStageContext(projectId: projectId);
    }
  }

  bool get isGenesisMode => projectsList.isEmpty;

  Future<void> completeCompanyActivation({
    required String companyName,
    required String industry,
    required String businessModel,
    required String vision,
    required String mission,
    required String projectTitle,
    required ProjectStage stage,
    required String jobToBeDone,
    required String problemStatement,
    required String currentAlternative,
  }) async {
    isStageLoading.value = true;
    try {
      // 1. Tạo Canvas & Foundation nếu có vision/mission
      try {
        final canvas = await strategyService.createCanvas(
          '$companyName - Chiến lược cốt lõi',
          description: 'Ngành: $industry • Mô hình: $businessModel',
        );
        final canvasId = canvas['canvas']?['id']?.toString() ?? canvas['id']?.toString();
        if (canvasId != null) {
          final rev = await strategyService.createRevision(canvasId);
          final revId = rev['revision']?['id']?.toString() ?? rev['id']?.toString();
          if (revId != null) {
            await strategyService.saveFoundation(
              revId,
              vision: vision.isNotEmpty ? vision : 'Xây dựng doanh nghiệp đột phá trong ngành $industry',
              mission: mission.isNotEmpty ? mission : 'Giải quyết triệt để nhu cầu của khách hàng thông qua $businessModel',
              values: [
                {'title': 'Tập trung khách hàng & JTBD', 'description': 'Giải quyết triệt để nỗi đau thực tế.'},
                {'title': 'Tốc độ thực thi AI', 'description': 'Tối ưu hoá hiệu suất với AI Autonomous.'},
                {'title': 'Bằng chứng thực tế', 'description': 'Quyết định dựa trên dữ liệu và WTP.'},
              ],
            );
          }
        }
      } catch (e) {
        debugPrint('[Genesis] Canvas/Foundation setup note: $e');
      }

      // 2. Tạo First Project với đúng Stage được chọn
      final projectRes = await strategyService.createProject(
        title: projectTitle,
        description: 'Mô hình: $businessModel • Ngành: $industry\nJTBD: $jobToBeDone\nProblem: $problemStatement\nAlternative: $currentAlternative',
        projectStage: stage.code,
        stageGoal: 'Xác thực mục tiêu trọng tâm của giai đoạn ${stage.code}',
        status: 'active',
        startDate: DateTime.now(),
      );

      final newProjId = int.tryParse(
        projectRes['project']?['id']?.toString() ?? projectRes['id']?.toString() ?? '',
      );

      // 3. Đánh giá và sinh Next Best Actions đầu tiên
      try {
        await strategyService.evaluateCeoNextActions(
          projectId: newProjId?.toString(),
        );
      } catch (e) {
        debugPrint('[Genesis] Evaluate next actions note: $e');
      }

      // 4. Tải lại toàn bộ dữ liệu Hub & Stage
      await loadProjectsList();
      if (newProjId != null) {
        selectedProjectId.value = newProjId;
        await loadStageContext(projectId: newProjId);
      } else {
        await loadStageContext();
      }

      AppToast.success(
        'Hệ điều hành COSA AI đã sẵn sàng cùng dự án "$projectTitle"!',
        title: 'Kích hoạt thành công',
      );
    } catch (e) {
      debugPrint('[Genesis] Activation error: $e');
      AppToast.error(
        'Không thể hoàn tất thiết lập: $e',
        title: 'Lỗi kích hoạt',
      );
    } finally {
      isStageLoading.value = false;
    }
  }

  // ── Must be implemented by domain mixins ─────────────────────────────────
  Future<void> loadEvidenceData(int? projectId);
  Future<void> loadStageLensesData(int? projectId);
  Future<void> loadStageGateData(int? projectId);
}
