import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../controllers/workspace_runtime_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class NeedsYouView extends StatelessWidget {
  const NeedsYouView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<WorkspaceRuntimeController>()) {
      Get.put(WorkspaceRuntimeController());
    }
    final controller = Get.find<WorkspaceRuntimeController>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        JavisFloatingAppBar(
          title: 'Cần bạn xử lý (Needs You)',
          subtitle: 'Hàng đợi ngoại lệ & các quyết định cần Founder / người điều hành phê duyệt',
          icon: Icons.notification_important_rounded,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh, color: AppTheme.primary),
              onPressed: controller.loadNeedsYou,
              tooltip: 'Tải lại',
            ),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            final result = controller.needsYouResult.value;

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
                          ? 'Bạn không có quyền truy cập hàng đợi này.'
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
                      onPressed: controller.loadNeedsYou,
                      child: const Text('Thử lại'),
                    ),
                  ],
                ),
              );
            }

            final items = controller.needsYouItems;

            if (items.isEmpty) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.check_circle_outline, size: 64, color: AppTheme.success),
                    const SizedBox(height: 16),
                    Text(
                      'Tuyệt vời! Không có việc gì cần xử lý ngay bây giờ.',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white70),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Mọi ngoại lệ quy trình sẽ hiển thị ở đây khi cần sự can thiệp của Founder.',
                      style: TextStyle(color: Colors.white38, fontSize: 13),
                    ),
                  ],
                ),
              );
            }

            return RefreshIndicator(
              onRefresh: controller.loadNeedsYou,
              child: ListView.builder(
                padding: EdgeInsets.zero,
                itemCount: items.length,
                itemBuilder: (context, index) {
                  final item = items[index];
                  final isHighPrio = item.severity == 'HIGH' || item.severity == 'CRITICAL';

                  return Card(
                    color: const Color(0xFF1E293B),
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: BorderSide(
                        color: isHighPrio ? AppTheme.warning.withValues(alpha: 0.5) : Colors.white10,
                      ),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: isHighPrio ? AppTheme.warning.withValues(alpha: 0.2) : Colors.white10,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  item.severity,
                                  style: TextStyle(
                                    color: isHighPrio ? AppTheme.warning : Colors.white70,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 11,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                item.sourceRef.kind.toUpperCase(),
                                style: const TextStyle(color: Colors.white54, fontSize: 12),
                              ),
                              const Spacer(),
                              Text(
                                item.createdAt.length >= 10 ? item.createdAt.substring(0, 10) : item.createdAt,
                                style: const TextStyle(color: Colors.white38, fontSize: 12),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            item.title,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                          if (item.description != null && item.description!.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text(
                              item.description!,
                              style: const TextStyle(color: Colors.white70, fontSize: 14),
                            ),
                          ],
                          const SizedBox(height: 14),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton.icon(
                                icon: const Icon(Icons.snooze, size: 16, color: Colors.white60),
                                label: const Text('Hoãn 1 ngày', style: TextStyle(color: Colors.white60)),
                                onPressed: () {
                                  final until = DateTime.now().add(const Duration(days: 1));
                                  controller.snoozeNeedsYou(item.sourceKind, item.sourceId, until);
                                },
                              ),
                              const SizedBox(width: 8),
                              ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppTheme.primary,
                                  foregroundColor: Colors.white,
                                ),
                                icon: const Icon(Icons.open_in_new, size: 16),
                                label: const Text('Xem chi tiết'),
                                onPressed: () {
                                  controller.loadInspector(item.sourceKind, item.sourceId);
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
