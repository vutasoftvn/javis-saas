import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/module_routes.dart';
import '../../../../core/services/feature_flags_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/feature_not_enabled_view.dart';
import '../../../hologram_hub/views/hologram_hub_view.dart';
import '../../../organization/views/organization_view.dart';
import '../../../skills/views/skill_registry_view.dart';
import '../../../strategy/views/okrs_view.dart';
import '../../../strategy/views/project_funding_view.dart';
import '../../../strategy/views/project_roadmap_view.dart';
import '../../../strategy/views/template_library_view.dart';
import '../../../strategy/views/twelve_week_year_view.dart';
import '../../../workspace_runtime/views/blocked_work_view.dart';
import '../../../workspace_runtime/views/needs_you_view.dart';
import '../../../workspace_runtime/views/work_inspector_view.dart';
import '../../controllers/dashboard_controller.dart';
import '../../models/dashboard_nav_config.dart';

/// Task 9 — trước đây widget này là "authority" DUY NHẤT chọn view bằng một
/// index nguyên (switch 0..33), không thể deep-link/back-stack/guard riêng
/// từng mục. Nay chỉ còn giữ các mục CHƯA có route canonical
/// (`WorkspaceModule`) — xem `module_routes.dart`. Mục ĐÃ migrate không còn
/// build view tại đây nữa: `_buildFeatureView` trở thành một "redirect
/// adapter" tạm thời, điều hướng sang route thật thay vì render inline.
///
/// Switch chỉ được XOÁ HẲN khi mọi mục sidebar đều có route canonical — hiện
/// tại còn ~10 mục (OKRs, 12WY, roadmap, template library, project funding,
/// needs-you, blocked-work, work-inspector, organization, skill registry)
/// chưa có route riêng, nên adapter này còn cần thiết (đúng tinh thần "retain
/// feature pages initially" của Task 9).
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
    // Redirect adapter: mục này đã có route canonical thật — điều hướng
    // sang đó thay vì render trực tiếp. Không dùng cho `index == 0` (hub) vì
    // hub CHÍNH LÀ route đang host widget này.
    final module = moduleForLegacyIndex(index);
    if (module != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (Get.currentRoute != module.path) {
          Get.toNamed(module.path);
        }
      });
      return const Center(child: CircularProgressIndicator());
    }

    switch (index) {
      case 0:
        return const HologramHubView();
      case 19:
        return const OrganizationView();
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
