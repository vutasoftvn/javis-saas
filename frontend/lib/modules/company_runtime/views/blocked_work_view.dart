import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/company_runtime_controller.dart';
import '../../../core/theme/app_theme.dart';

class BlockedWorkView extends StatelessWidget {
  const BlockedWorkView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<CompanyRuntimeController>()) {
      Get.put(CompanyRuntimeController());
    }
    final controller = Get.find<CompanyRuntimeController>();

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Blocked Work & Exceptions'),
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => controller.loadBlockers(),
          ),
        ],
      ),
      body: Obx(() {
        if (controller.loading.value && controller.blockers.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        if (controller.blockers.isEmpty) {
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
            padding: const EdgeInsets.all(20),
            itemCount: controller.blockers.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final blocker = controller.blockers[index] as Map<String, dynamic>;
              final function = (blocker['assigned_function'] ?? 'FOUNDER').toString();
              final blockerType = (blocker['blocker_type'] ?? 'BLOCKER').toString();
              final status = (blocker['status'] ?? 'OPEN').toString();

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
                              function,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                            backgroundColor: Colors.indigo.withValues(alpha: 0.3),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            blockerType,
                            style: const TextStyle(color: Colors.amberAccent, fontSize: 12),
                          ),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: status == 'RESOLVED'
                                  ? Colors.green.withValues(alpha: 0.2)
                                  : Colors.orange.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              status,
                              style: TextStyle(
                                color: status == 'RESOLVED' ? Colors.greenAccent : Colors.orangeAccent,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        blocker['description'] ?? 'Chi tiết blocker',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 14),
                      if (status != 'RESOLVED')
                        Align(
                          alignment: Alignment.centerRight,
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.primary,
                              foregroundColor: Colors.white,
                            ),
                            icon: const Icon(Icons.check, size: 16),
                            label: const Text('Giải tỏa Blocker'),
                            onPressed: () {
                              controller.resolveBlocker(blocker['id'].toString());
                            },
                          ),
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
