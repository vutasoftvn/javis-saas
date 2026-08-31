import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/services/feature_flags_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/feature_not_enabled_view.dart';
import '../../../agents/views/agents_view.dart';
import '../../../approvals/views/approvals_view.dart';
import '../../../finance/views/finance_view.dart';
import '../../../hologram_hub/views/hologram_hub_view.dart';
import '../../../legal/views/legal_view.dart';
import '../../../marketing/views/marketing_cockpit_view.dart';
import '../../../organization/views/organization_view.dart';
import '../../../sales/views/sales_view.dart';
import '../../../settings/views/settings_view.dart';
import '../../../skills/views/skill_registry_view.dart';
import '../../../strategy/views/okrs_view.dart';
import '../../../strategy/views/project_funding_view.dart';
import '../../../strategy/views/project_roadmap_view.dart';
import '../../../strategy/views/strategy_view.dart';
import '../../../strategy/views/template_library_view.dart';
import '../../../strategy/views/twelve_week_year_view.dart';
import '../../../tasks/views/tasks_view.dart';
import '../../../vault/views/vault_view.dart';
import '../../../workflows/views/workflows_view.dart';
import '../../../workspace_runtime/views/blocked_work_view.dart';
import '../../../workspace_runtime/views/needs_you_view.dart';
import '../../../workspace_runtime/views/work_inspector_view.dart';
import '../../controllers/dashboard_controller.dart';
import '../../models/dashboard_nav_config.dart';

class DashboardContentBody extends StatelessWidget {
  final DashboardController controller;

  const DashboardContentBody({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final index = controller.currentIndex.value;
      final item = DashboardNavConfig.allNavItems.firstWhereOrNull((candidate) => candidate.index == index);
      if (item?.flagKey != null && !Get.find<FeatureFlagsController>().isEnabled(item!.flagKey!)) {
        return FeatureNotEnabledView(featureName: item.label);
      }
      try {
        return _buildFeatureView(index);
      } catch (e) {
        return _errorView(e.toString());
      }
    });
  }

  Widget _buildFeatureView(int index) {
    switch (index) {
      case 0:
        return const HologramHubView();
      case 1:
        return const TasksView();
      case 2:
        return const VaultView();
      case 3:
        return StrategyView(
          key: ValueKey('strategy_view_${controller.strategyInitialTabIndex.value}'),
          initialTabIndex: controller.strategyInitialTabIndex.value,
        );
      case 5:
        return const WorkflowsView();
      case 6:
        return const ApprovalsView();
      case 7:
        return const AgentsView();
      case 13:
        return const SettingsView();
      case 17:
        return const MarketingCockpitView();
      case 19:
        return const OrganizationView();
      case 21:
        return const FinanceView();
      case 22:
        return const LegalView();
      case 23:
        return const SalesView();
      case 24:
        return const NeedsYouView();
      case 25:
        return const BlockedWorkView();
      case 26:
        return const WorkInspectorView();
      case 27:
        return const OkrsView();
      case 28:
        return const TwelveWeekYearView();
      case 29:
        return const ProjectRoadmapView();
      case 30:
        return const TemplateLibraryView();
      case 32:
        return const ProjectFundingView();
      case 33:
        return const SkillRegistryView();
      default:
        return const HologramHubView();
    }
  }

  Widget _errorView(String error) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.error, size: 48),
              const SizedBox(height: 16),
              Text(
                'Không thể tải tính năng:\n$error',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.error, fontSize: 14),
              ),
            ],
          ),
        ),
      );
}
