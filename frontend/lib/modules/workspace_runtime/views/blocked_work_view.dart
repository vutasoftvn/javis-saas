import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../controllers/workspace_runtime_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class BlockedWorkView extends StatelessWidget {
  const BlockedWorkView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<WorkspaceRuntimeController>()) {
      Get.put(WorkspaceRuntimeController());
    }
    final controller = Get.find<WorkspaceRuntimeController>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CosaFloatingAppBar(
          title: 'Công việc tắc nghẽn (Blocked Work)',
          subtitle: 'Giám sát và gỡ bỏ các điểm nghẽn phụ thuộc giữa AI Agents & Founder',
          icon: Icons.block_rounded,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh, color: AppTheme.primary),
              onPressed: () => controller.loadBlockers(),
              tooltip: 'Tải lại',
            ),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            final result = controller.blockersResult.value;

            if (controller.loading.value && result == null) {
              return const Center(child: CircularProgressIndicator());
            }

            if (result is ApiFailure) {
              final failure = (result as ApiFailure).failure;
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.warning_amber_rounded, size: 64, color: AppTheme.warning),
                    const SizedBox(height: 16),
                    Text(
                      failure.code == ApiFailureCode.forbidden
                          ? 'Bạn không có quyền truy cập thông tin tắc nghẽn.'
                          : 'Dịch vụ tạm thời không khả dụng.',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white70),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      failure.message,
                      style: const TextStyle(color: Colors.white38, fontSize: 13),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () => controller.loadBlockers(),
                      child: const Text('Thử lại'),
                    ),
                  ],
                ),
              );
            }

            final blockers = controller.blockers;

            if (blockers.isEmpty) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.task_alt, size: 64, color: AppTheme.success),
                    const SizedBox(height: 16),
                    Text(
                      'Không có công việc nào bị nghẽn (No Blockers)',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white70),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Tất cả các luồng phụ thuộc đang chạy bình thường.',
                      style: TextStyle(color: Colors.white38),
                    ),
                  ],
                ),
              );
            }

            return RefreshIndicator(
              onRefresh: () => controller.loadBlockers(),
              child: ListView.separated(
                padding: EdgeInsets.zero,
                itemCount: blockers.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final blocker = blockers[index];

                  return Card(
                    color: const Color(0xFF1E293B),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(color: Colors.white10),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Chip(
                                label: Text(
                                  blocker.sourceRef.kind.toUpperCase(),
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                                ),
                                backgroundColor: Colors.indigo.withValues(alpha: 0.3),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                blocker.state,
                                style: const TextStyle(color: Colors.amberAccent, fontSize: 12),
                              ),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: Colors.red.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  blocker.severity,
                                  style: const TextStyle(
                                    color: Colors.redAccent,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            blocker.title,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                          if (blocker.description != null && blocker.description!.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text(
                              blocker.description!,
                              style: const TextStyle(color: Colors.white70, fontSize: 14),
                            ),
                          ],
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppTheme.primary,
                                  foregroundColor: Colors.white,
                                ),
                                icon: const Icon(Icons.search, size: 16),
                                label: const Text('Kiểm tra tác vụ'),
                                onPressed: () {
                                  controller.loadInspector(blocker.sourceKind, blocker.sourceId);
                                },
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            );
          }),
        ),
      ],
    );
  }
}
