import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../audit/controllers/audit_controller.dart';
import '../../channels/controllers/channels_controller.dart';
import '../../chatbots/controllers/chatbots_controller.dart';
import '../../settings/controllers/settings_controller.dart';
import '../../branding/controllers/branding_controller.dart';
import '../../backup/controllers/backup_controller.dart';
import '../../diagnostics/controllers/diagnostics_controller.dart';
import '../../approvals/controllers/approvals_controller.dart';
import '../../agents/controllers/agents_controller.dart';
import '../../connections/controllers/connections_controller.dart';
import '../../plugins/controllers/plugins_controller.dart';
import '../../workflows/controllers/workflows_controller.dart';
import '../../marketing/controllers/marketing_controller.dart';
import '../../../core/services/feature_flags_controller.dart';

class DashboardBinding extends Bindings {
  @override
  void dependencies() {
    Get.put<FeatureFlagsController>(FeatureFlagsController(), permanent: true);
    Get.lazyPut<DashboardController>(() => DashboardController());
    Get.lazyPut<AuditController>(() => AuditController());
    Get.lazyPut<ChannelsController>(() => ChannelsController());
    Get.lazyPut<ChatbotsController>(() => ChatbotsController());
    Get.lazyPut<SettingsController>(() => SettingsController());
    Get.lazyPut<BrandingController>(() => BrandingController());
    Get.lazyPut<BackupController>(() => BackupController());
    Get.lazyPut<DiagnosticsController>(() => DiagnosticsController());
    Get.lazyPut<ApprovalsController>(() => ApprovalsController());
    Get.lazyPut<AgentsController>(() => AgentsController());
    Get.lazyPut<ConnectionsController>(() => ConnectionsController());
    Get.lazyPut<PluginsController>(() => PluginsController());
    Get.lazyPut<WorkflowsController>(() => WorkflowsController());
    Get.lazyPut<MarketingController>(() => MarketingController());
  }
}
