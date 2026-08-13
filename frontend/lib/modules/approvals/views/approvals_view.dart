import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/approvals_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class ApprovalsView extends GetView<ApprovalsController> {
  const ApprovalsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ApprovalsController>()) {
      Get.put(ApprovalsController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        JavisFloatingAppBar(
          title: 'Phê duyệt & Kiểm soát',
          subtitle: 'Kiểm tra và phê duyệt các hành động AI, external tools hoặc thay đổi quan trọng.',
          icon: Icons.fact_check_rounded,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh, color: AppTheme.primary),
              tooltip: 'Tải lại',
              onPressed: controller.loadApprovals,
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Tab Bar
        Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: TabBar(
            controller: controller.tabController,
            indicator: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.primary),
            ),
            labelColor: AppTheme.primary,
            unselectedLabelColor: AppTheme.textMutedDark,
            indicatorSize: TabBarIndicatorSize.tab,
            tabs: const [
              Tab(text: 'Chờ duyệt'),
              Tab(text: 'Lịch sử'),
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
                _buildPendingList(context),
                _buildHistoryList(context),
              ],
            );
          }),
        ),
      ],
    );
  }

  Widget _buildPendingList(BuildContext context) {
    if (controller.pendingApprovals.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.check_circle_outline, size: 54, color: Color(0xFF10B981)),
            SizedBox(height: 16),
            Text(
              'Không có yêu cầu chờ duyệt',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            SizedBox(height: 4),
            Text(
              'Tất cả các hành động AI và workflow đang chạy bình thường.',
              style: TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: controller.pendingApprovals.length,
      itemBuilder: (context, index) {
        final item = controller.pendingApprovals[index];
        final stepId = item['step_id'] as String? ?? '';
        final nodeId = item['node_id'] as String? ?? 'Nút hành động';
        final createdAt = item['created_at'] as String? ?? '';

        return Container(
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.4)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.25),
                blurRadius: 10,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.pending_actions, color: Color(0xFFF59E0B), size: 20),
                      ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Hành động: $nodeId',
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                          Text(
                            'Step ID: ${stepId.length > 8 ? stepId.substring(0, 8) : stepId}... · $createdAt',
                            style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                          ),
                        ],
                      ),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFF59E0B)),
                    ),
                    child: const Text(
                      'CHỜ PHÊ DUYỆT',
                      style: TextStyle(color: Color(0xFFF59E0B), fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              if (item['snapshot_payload'] != null)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF070C18),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Text(
                    '${item['snapshot_payload']}',
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Color(0xFFCBD5E1)),
                  ),
                ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => controller.reject(stepId),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFEF4444),
                      side: const BorderSide(color: Color(0xFFEF4444)),
                      minimumSize: const Size(64, 44),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                    ),
                    icon: const Icon(Icons.close, size: 16),
                    label: const Text('Từ chối'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: () => controller.approve(stepId),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: Colors.white,
                      minimumSize: const Size(64, 44),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                    ),
                    icon: const Icon(Icons.check, size: 16),
                    label: const Text('Phê duyệt & Tiếp tục'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHistoryList(BuildContext context) {
    if (controller.historyApprovals.isEmpty) {
      return const Center(
        child: Text('Chưa có lịch sử phê duyệt', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }

    return ListView.builder(
      itemCount: controller.historyApprovals.length,
      itemBuilder: (context, index) {
        final item = controller.historyApprovals[index];
        final status = item['status'] as String? ?? '';
        final isApproved = status == 'approved';
        final nodeId = item['node_id'] as String? ?? 'Nút hành động';
        final reviewedAt = item['reviewed_at'] as String? ?? item['created_at'] ?? '';

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
                isApproved ? Icons.check_circle : Icons.cancel,
                color: isApproved ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                size: 24,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hành động: $nodeId',
                      style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    Text(
                      'Đã xử lý lúc: $reviewedAt',
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: isApproved
                      ? const Color(0xFF10B981).withValues(alpha: 0.15)
                      : const Color(0xFFEF4444).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  isApproved ? 'ĐÃ DUYỆT' : 'TỪ CHỐI',
                  style: TextStyle(
                    color: isApproved ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
