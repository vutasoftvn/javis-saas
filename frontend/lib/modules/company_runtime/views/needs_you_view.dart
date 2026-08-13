import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/company_runtime_controller.dart';
import '../../../core/theme/app_theme.dart';

class NeedsYouView extends StatelessWidget {
  const NeedsYouView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<CompanyRuntimeController>()) {
      Get.put(CompanyRuntimeController());
    }
    final controller = Get.find<CompanyRuntimeController>();

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Needs You — Founder Exception Queue'),
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: controller.loadNeedsYou,
          ),
        ],
      ),
      body: Obx(() {
        if (controller.loading.value && controller.needsYouItems.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        if (controller.needsYouItems.isEmpty) {
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
                  'Các AI Function đang vận hành trơn tru.',
                  style: TextStyle(color: Colors.white38),
                ),
              ],
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: controller.loadNeedsYou,
          child: ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: controller.needsYouItems.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final item = controller.needsYouItems[index] as Map<String, dynamic>;
              final priority = (item['priority'] ?? 'P1').toString();
              final isP0 = priority == 'P0';

              return Card(
                color: const Color(0xFF1E293B),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(
                    color: isP0 ? Colors.redAccent.withValues(alpha: 0.5) : Colors.white10,
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
                              color: isP0 ? Colors.red.withValues(alpha: 0.2) : Colors.amber.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              priority,
                              style: TextStyle(
                                color: isP0 ? Colors.redAccent : Colors.amber,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            (item['source_type'] ?? 'EXCEPTION').toString().toUpperCase(),
                            style: const TextStyle(color: Colors.white54, fontSize: 12),
                          ),
                          const Spacer(),
                          Text(
                            item['created_at'] != null
                                ? item['created_at'].toString().split('T').first
                                : '',
                            style: const TextStyle(color: Colors.white38, fontSize: 11),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        item['reason'] ?? 'Cần quyết định từ founder',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (item['requested_action'] != null) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Hành động yêu cầu: ${item['requested_action']}',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
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
                              controller.snoozeNeedsYou(item['id'].toString(), until);
                            },
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.primary,
                              foregroundColor: Colors.white,
                            ),
                            icon: const Icon(Icons.check, size: 16),
                            label: const Text('Đã xử lý'),
                            onPressed: () {
                              controller.resolveNeedsYou(item['id'].toString());
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
    );
  }
}
