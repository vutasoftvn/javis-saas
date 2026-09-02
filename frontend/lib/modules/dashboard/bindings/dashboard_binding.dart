import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../hologram_hub/controllers/hologram_hub_controller.dart';
import '../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../../strategy/controllers/strategy_controller.dart';
import '../../strategy/controllers/project_orchestration_controller.dart';
import '../../strategy/controllers/foundation_controller.dart';
import '../../organization/controllers/organization_controller.dart';
import '../../workspace_runtime/controllers/workspace_runtime_controller.dart';
import '../../skills/controllers/skill_registry_controller.dart';
import '../../mission_control/controllers/mission_control_controller.dart';
import '../../../core/services/feature_flags_controller.dart';

/// Task 9 Step 3 — trước đây binding này eager-load TOÀN BỘ controller của
/// mọi module workspace (Tasks/Vault/Approvals/Agents/Workflows/Marketing/
/// Sales+SalesToday+Funnel/Finance/Legal/Settings) dù người dùng chưa mở
/// module nào — mỗi lần vào `/hub`/`/dashboard` đều dựng ~20 controller.
///
/// Các module ĐÃ có route canonical riêng (`module_routes.dart`) nay tự
/// đăng ký controller của mình qua binding riêng khi vào route, và tự huỷ
/// khi rời route (hành vi mặc định của `Get.lazyPut` gắn với `GetPage`) —
/// `DashboardBinding` không còn cần đăng ký hộ chúng nữa.
///
/// Những gì còn lại ở đây là dependency cho các mục sidebar CHƯA migrate
/// (vẫn hiển thị qua `DashboardContentBody` tại `/hub`): hub/founder command
/// center (index 0), strategy family — dùng chung bởi CẢ `/work/strategy`
/// LẪN các sub-view chưa migrate okrs/12WY/roadmap/template-library/funding
/// (index 27/28/29/30/32), organization (19), workspace runtime — needs-you/
/// blocked-work/work-inspector (24/25/26), skill registry (33), mission
/// control. KHÔNG được xoá các controller này khỏi đây cho tới khi các mục
/// sidebar tương ứng cũng có route canonical riêng.
class DashboardBinding extends Bindings {
  @override
  void dependencies() {
    Get.put<FeatureFlagsController>(FeatureFlagsController(), permanent: true);
    Get.lazyPut<DashboardController>(() => DashboardController());
    Get.lazyPut<HologramHubController>(() => HologramHubController());
    Get.lazyPut<FounderCommandCenterController>(() => FounderCommandCenterController());
    Get.lazyPut<StrategyController>(() => StrategyController());
    Get.lazyPut<ProjectOrchestrationController>(() => ProjectOrchestrationController());
    Get.lazyPut<FoundationController>(() => FoundationController());
    Get.lazyPut<OrganizationController>(() => OrganizationController());
    Get.lazyPut<WorkspaceRuntimeController>(() => WorkspaceRuntimeController());
    Get.lazyPut<SkillRegistryController>(() => SkillRegistryController());
    Get.lazyPut<MissionControlController>(() => MissionControlController());
  }
}
