import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/workflows_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class WorkflowsView extends GetView<WorkflowsController> {
  const WorkflowsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<WorkflowsController>()) {
      Get.put(WorkflowsController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CosaFloatingAppBar(
          title: 'Tự động hóa & Workflows',
          subtitle: 'Quản lý sơ đồ quy trình tự động, thực thi đa tác tử AI và giám sát luồng chạy.',
          icon: Icons.account_tree_rounded,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh, color: AppTheme.primary),
              tooltip: 'Tải lại',
              onPressed: controller.loadData,
            ),
          ],
        ),
        const SizedBox(height: 12),

            // Tab Bar
            Container(
              height: 38,
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: TabBar(
                controller: controller.tabController,
                indicatorSize: TabBarIndicatorSize.tab,
                dividerColor: Colors.transparent,
                padding: EdgeInsets.zero,
                labelPadding: EdgeInsets.zero,
                indicator: BoxDecoration(
                  borderRadius: BorderRadius.circular(7),
                  color: AppTheme.primary,
                ),
                labelColor: const Color(0xFF04070E),
                unselectedLabelColor: AppTheme.textMutedDark,
                tabs: [
                  Obx(() => Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('Định nghĩa quy trình', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                        const SizedBox(width: 8),
                        Text('(${controller.definitions.length})', style: const TextStyle(fontSize: 12)),
                      ],
                    ),
                  )),
                  Obx(() => Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('Lịch sử chạy (Runs)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                        const SizedBox(width: 8),
                        Text('(${controller.runs.length})', style: const TextStyle(fontSize: 12)),
                      ],
                    ),
                  )),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Tab Views
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value) {
                  return const Center(child: CircularProgressIndicator());
                }

                return TabBarView(
                  controller: controller.tabController,
                  children: [
                    _buildDefinitionsTab(context),
                    _buildRunsTab(context),
                  ],
                );
              }),
            ),
          ],
        );
  }

  Widget _buildDefinitionsTab(BuildContext context) {
    if (controller.definitions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.account_tree_outlined, size: 54, color: AppTheme.textMutedDark),
            SizedBox(height: 16),
            Text(
              'Chưa có định nghĩa workflow nào',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            SizedBox(height: 4),
            Text(
              'Tạo workflow mới để bắt đầu tự động hóa quy trình nghiệp vụ.',
              style: TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: controller.definitions.length,
      itemBuilder: (context, index) {
        final def = controller.definitions[index];
        final defId = def['id'] as String? ?? '';
        final slug = def['slug'] as String? ?? 'workflow-definition';
        final createdAt = def['created_at'] as String? ?? '';

        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.hub_outlined, color: Color(0xFF00F0FF), size: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      slug,
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'ID: $defId · Tạo lúc: $createdAt',
                      style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                onPressed: () => controller.triggerRun(defId),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00F0FF).withValues(alpha: 0.2),
                  foregroundColor: const Color(0xFF00F0FF),
                  side: const BorderSide(color: Color(0xFF00F0FF)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                ),
                icon: const Icon(Icons.play_arrow, size: 16),
                label: const Text('Chạy ngay', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildRunsTab(BuildContext context) {
    if (controller.runs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.history, size: 54, color: AppTheme.textMutedDark),
            SizedBox(height: 16),
            Text(
              'Chưa có lần chạy workflow nào',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            SizedBox(height: 4),
            Text(
              'Nhấn "Chạy ngay" ở tab Định nghĩa để khởi chạy lần đầu tiên.',
              style: TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: controller.runs.length,
      itemBuilder: (context, index) {
        final run = controller.runs[index];
        final runId = run['id'] as String? ?? '';
        final status = run['status'] as String? ?? 'running';
        final trigger = run['trigger'] as String? ?? 'manual';
        final createdAt = run['created_at'] as String? ?? '';

        final isRunning = status == 'running';
        final isCompleted = status == 'completed';
        final statusColor = isRunning
            ? const Color(0xFF00F0FF)
            : (isCompleted ? const Color(0xFF10B981) : const Color(0xFFEF4444));

        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            children: [
              Icon(
                isRunning ? Icons.autorenew : (isCompleted ? Icons.check_circle : Icons.error_outline),
                color: statusColor,
                size: 22,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Run #${runId.length > 8 ? runId.substring(0, 8) : runId}',
                      style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    Text(
                      'Trigger: $trigger · Bắt đầu lúc: $createdAt',
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  status.toUpperCase(),
                  style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
