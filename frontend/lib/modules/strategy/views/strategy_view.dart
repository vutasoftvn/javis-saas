import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../projects/views/project_operating_loop_view.dart';
import '../controllers/strategy_controller.dart';

class StrategyView extends GetView<StrategyController> {
  final int initialTabIndex;
  const StrategyView({super.key, this.initialTabIndex = 0});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }

    return Obx(() {
      final pid = controller.activeProjectId.value;
      if (pid != null && pid.isNotEmpty) {
        return ProjectOperatingLoopView(projectId: pid);
      }

      return Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.rocket_launch_outlined, size: 64, color: AppTheme.primary),
              const SizedBox(height: 16),
              Text(
                'Project Operating Loop',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Select or create a project to start the operating loop.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppTheme.textMutedDark,
                ),
              ),
            ],
          ),
        ),
      );
    });
  }
}
