import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../hologram_hub/controllers/hologram_hub_controller.dart';
import '../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../../tasks/controllers/tasks_controller.dart';
import '../../vault/controllers/vault_controller.dart';
import '../../strategy/controllers/strategy_controller.dart';
import '../../strategy/controllers/project_orchestration_controller.dart';
import '../../strategy/controllers/foundation_controller.dart';
import '../../approvals/controllers/approvals_controller.dart';
import '../../agents/controllers/agents_controller.dart';
import '../../workflows/controllers/workflows_controller.dart';
import '../../marketing/controllers/marketing_controller.dart';
import '../../sales/controllers/sales_controller.dart';
import '../../sales/controllers/sales_today_controller.dart';
import '../../sales/controllers/funnel_controller.dart';
import '../../finance/controllers/finance_controller.dart';
import '../../legal/controllers/legal_controller.dart';
import '../../organization/controllers/organization_controller.dart';
import '../../settings/controllers/settings_controller.dart';
import '../../company_runtime/controllers/company_runtime_controller.dart';
import '../../skills/controllers/skill_registry_controller.dart';
import '../../mission_control/controllers/mission_control_controller.dart';
import '../../../core/services/feature_flags_controller.dart';

class DashboardBinding extends Bindings {
  @override
  void dependencies() {
    Get.put<FeatureFlagsController>(FeatureFlagsController(), permanent: true);
    Get.lazyPut<DashboardController>(() => DashboardController());
    Get.lazyPut<HologramHubController>(() => HologramHubController());
    Get.lazyPut<FounderCommandCenterController>(() => FounderCommandCenterController());
    Get.lazyPut<TasksController>(() => TasksController());
    Get.lazyPut<VaultController>(() => VaultController());
    Get.lazyPut<StrategyController>(() => StrategyController());
    Get.lazyPut<ProjectOrchestrationController>(() => ProjectOrchestrationController());
    Get.lazyPut<FoundationController>(() => FoundationController());
    Get.lazyPut<ApprovalsController>(() => ApprovalsController());
    Get.lazyPut<AgentsController>(() => AgentsController());
    Get.lazyPut<WorkflowsController>(() => WorkflowsController());
    Get.lazyPut<MarketingController>(() => MarketingController());
    Get.lazyPut<SalesController>(() => SalesController());
    Get.lazyPut<SalesTodayController>(() => SalesTodayController());
    Get.lazyPut<FunnelController>(() => FunnelController());
    Get.lazyPut<FinanceController>(() => FinanceController());
    Get.lazyPut<LegalController>(() => LegalController());
    Get.lazyPut<OrganizationController>(() => OrganizationController());
    Get.lazyPut<SettingsController>(() => SettingsController());
    Get.lazyPut<CompanyRuntimeController>(() => CompanyRuntimeController());
    Get.lazyPut<SkillRegistryController>(() => SkillRegistryController());
    Get.lazyPut<MissionControlController>(() => MissionControlController());
  }
}

