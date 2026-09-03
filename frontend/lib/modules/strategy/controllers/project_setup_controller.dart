import 'package:get/get.dart';

import '../../../core/routing/app_routes.dart';
import '../../../core/routing/module_routes.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../services/strategy_service.dart';

/// Hai pha của luồng thiết lập project: nhập tên/mô tả rồi tới kickoff 3 bước.
enum ProjectSetupPhase { form, kickoff }

/// Điều phối route `/projects/new`. Mode-aware: onboarding (`projectCount == 0`)
/// không cho Huỷ; project thứ N có Huỷ. Kickoff tái dùng `ProjectKickoffView`.
class ProjectSetupController extends GetxController {
  final Rx<ProjectSetupPhase> phase = ProjectSetupPhase.form.obs;
  final RxnString createdProjectId = RxnString();
  final RxBool isSubmitting = false.obs;
  final RxnString formError = RxnString();

  FounderCommandCenterController get _fcc =>
      Get.find<FounderCommandCenterController>();

  bool get isOnboarding => _fcc.projectsList.isEmpty;

  @override
  void onInit() {
    super.onInit();
    // Resume: đúng 1 project và setup chưa ACTIVE -> vào thẳng kickoff của nó.
    if (_fcc.projectsList.length == 1 &&
        _fcc.activeProjectSetup.value?.status != OperatingSetupStatus.active) {
      createdProjectId.value = _fcc.projectsList.first['id']?.toString();
      if ((createdProjectId.value ?? '').isNotEmpty) {
        phase.value = ProjectSetupPhase.kickoff;
      }
    }
  }

  Future<void> submitForm({required String title, String? description}) async {
    final trimmed = title.trim();
    if (trimmed.isEmpty) {
      formError.value = 'Vui lòng nhập tên dự án';
      return;
    }
    formError.value = null;
    isSubmitting.value = true;
    try {
      final project = await StrategyService()
          .createBasicProject(title: trimmed, description: description?.trim());
      final id = project['id']?.toString();
      if (id == null || id.isEmpty) {
        formError.value = 'Tạo dự án thất bại. Vui lòng thử lại.';
        return;
      }
      createdProjectId.value = id;
      await _fcc.loadDashboardData();
      phase.value = ProjectSetupPhase.kickoff;
    } catch (e) {
      formError.value = 'Đã có lỗi xảy ra: $e';
    } finally {
      isSubmitting.value = false;
    }
  }

  void onKickoffActivated(String projectId) => Get.offAllNamed(AppRoutes.hub);

  void onKickoffBack() {
    if (isOnboarding) return;
    Get.offAllNamed(AppRoutes.hub);
  }

  void onOpenAdvancedRoadmap() => Get.toNamed(WorkspaceModule.strategy.path);

  void cancel() => Get.offAllNamed(AppRoutes.hub);
}
