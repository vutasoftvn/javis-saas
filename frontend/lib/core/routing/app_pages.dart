import 'package:get/get.dart';
import 'app_routes.dart';
import 'auth_middleware.dart';

import '../../modules/auth/views/login_view.dart';
import '../../modules/auth/views/register_view.dart';
import '../../modules/auth/bindings/auth_binding.dart';
import '../../modules/dashboard/views/dashboard_view.dart';
import '../../modules/dashboard/bindings/dashboard_binding.dart';
import '../../modules/hologram_hub/views/hologram_hub_view.dart';
import '../../modules/hologram_hub/bindings/hologram_hub_binding.dart';
import '../../modules/mission_control/views/mission_control_view.dart';
import '../../modules/mission_control/bindings/mission_control_binding.dart';
import '../../modules/approvals/views/approvals_view.dart';
import '../../modules/approvals/bindings/approvals_binding.dart';
import '../../modules/agents/views/agents_view.dart';
import '../../modules/agents/bindings/agents_binding.dart';
import '../../modules/tasks/views/tasks_view.dart';
import '../../modules/tasks/bindings/tasks_binding.dart';
import '../../modules/profile/views/profile_view.dart';
import '../../modules/profile/bindings/profile_binding.dart';
import '../../modules/company_picker/views/company_picker_view.dart';
import '../../modules/company_picker/bindings/company_picker_binding.dart';
import '../../modules/strategy/views/strategy_view.dart';
import '../../modules/strategy/bindings/strategy_binding.dart';
import '../../modules/vault/views/vault_view.dart';
import '../../modules/vault/bindings/vault_binding.dart';
import '../../modules/sales/views/sales_view.dart';
import '../../modules/sales/bindings/sales_binding.dart';
import '../../modules/marketing/views/marketing_cockpit_view.dart';
import '../../modules/marketing/bindings/marketing_binding.dart';
import '../../modules/finance/views/finance_view.dart';
import '../../modules/finance/bindings/finance_binding.dart';
import '../../modules/legal/views/legal_view.dart';
import '../../modules/legal/bindings/legal_binding.dart';
import '../../modules/workflows/views/workflows_view.dart';
import '../../modules/workflows/bindings/workflows_binding.dart';
import '../../modules/chat/views/chat_view.dart';
import '../../modules/chat/bindings/chat_binding.dart';

class AppPages {
  static const initial = AppRoutes.login;

  static final routes = [
    GetPage(
      name: AppRoutes.chat,
      page: () => const ChatView(),
      binding: ChatBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.login,
      page: () => const LoginView(),
      binding: AuthBinding(),
    ),
    GetPage(
      name: AppRoutes.register,
      page: () => const RegisterView(),
      binding: AuthBinding(),
    ),
    GetPage(
      name: AppRoutes.companyPicker,
      page: () => const CompanyPickerView(),
      binding: CompanyPickerBinding(),
    ),
    GetPage(
      name: AppRoutes.dashboard,
      page: () => const DashboardView(),
      binding: DashboardBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.hub,
      page: () => const HologramHubView(),
      binding: HologramHubBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.missionControl,
      page: () => const MissionControlView(),
      binding: MissionControlBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.approvals,
      page: () => const ApprovalsView(),
      binding: ApprovalsBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.agents,
      page: () => const AgentsView(),
      binding: AgentsBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.tasks,
      page: () => const TasksView(),
      binding: TasksBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.profile,
      page: () => const ProfileView(),
      binding: ProfileBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.strategy,
      page: () => const StrategyView(),
      binding: StrategyBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.vault,
      page: () => const VaultView(),
      binding: VaultBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.sales,
      page: () => const SalesView(),
      binding: SalesBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.marketing,
      page: () => const MarketingCockpitView(),
      binding: MarketingBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.finance,
      page: () => const FinanceView(),
      binding: FinanceBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.legal,
      page: () => const LegalView(),
      binding: LegalBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.workflows,
      page: () => const WorkflowsView(),
      binding: WorkflowsBinding(),
      middlewares: [AuthMiddleware()],
    ),
  ];
}
