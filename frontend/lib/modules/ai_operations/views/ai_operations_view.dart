import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../controllers/ai_operations_controller.dart';
import 'tabs/execution_artifacts_tab.dart';
import 'tabs/execution_health_tab.dart';
import 'tabs/execution_jobs_tab.dart';

class AiOperationsView extends GetView<AiOperationsController> {
  const AiOperationsView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: Obx(() {
                switch (controller.currentTab.value) {
                  case 0:
                    return const ExecutionJobsTab();
                  case 1:
                    return const ExecutionArtifactsTab();
                  case 2:
                    return const ExecutionHealthTab();
                  default:
                    return const ExecutionJobsTab();
                }
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDarkHeader,
        border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
                ),
                child: const Icon(Icons.precision_manufacturing, color: AppTheme.primary, size: 22),
              ),
              const SizedBox(width: 12),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Vận hành AI (AI Operations)',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Quản lý công việc thực thi cô lập, log phân tích và lưu trữ artifacts an toàn.',
                    style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildTabBar(),
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    final tabs = [
      {'index': 0, 'label': 'Công việc (Jobs)', 'icon': Icons.work_outline},
      {'index': 1, 'label': 'Kết quả (Artifacts)', 'icon': Icons.folder_zip_outlined},
      {'index': 2, 'label': 'Môi trường (Health)', 'icon': Icons.shield_outlined},
    ];

    return Obx(() {
      final active = controller.currentTab.value;
      return Row(
        children: tabs.map((t) {
          final isSelected = active == t['index'];
          return InkWell(
            onTap: () => controller.setTab(t['index'] as int),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(
                    color: isSelected ? AppTheme.primary : Colors.transparent,
                    width: 2,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    t['icon'] as IconData,
                    size: 16,
                    color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    t['label'] as String,
                    style: TextStyle(
                      color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      fontSize: 13.5,
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      );
    });
  }
}
