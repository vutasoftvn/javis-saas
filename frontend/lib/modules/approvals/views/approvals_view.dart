import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/models/approval_model.dart';
import '../../../features/_shared/presentation/feature_state_view.dart';
import '../controllers/approvals_controller.dart';
import 'widgets/approval_header_bar.dart';
import 'widgets/approval_risk_filter_bar.dart';
import 'widgets/approval_ticket_card.dart';
import 'widgets/approval_history_item.dart';

class ApprovalsView extends GetView<ApprovalsController> {
  const ApprovalsView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      body: Column(
        children: [
          // 1. Header Bar with Tabs & Refresh
          ApprovalHeaderBar(controller: controller),

          // 2. Tab Content Views
          Expanded(
            child: TabBarView(
              controller: controller.tabController,
              children: [
                _buildPendingTab(context),
                _buildHistoryTab(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPendingTab(BuildContext context) {
    return Column(
      children: [
        // Risk Filter Chips
        ApprovalRiskFilterBar(controller: controller),

        // List Content
        // Task 6 — `FeatureStateView` là nơi DUY NHẤT quyết định hiển thị gì:
        // copy ăn mừng "Tuyệt vời!" chỉ được vẽ trong nhánh `dataBuilder`
        // (tức là `listState` đã là `FeatureData` — 200 thật) khi danh sách
        // sau lọc risk thật sự rỗng. 401/403/503/timeout/malformed đều rơi
        // vào `FeatureFailure` và hiện UI "Không thể tải" + nút "Thử lại" —
        // không bao giờ trông giống trạng thái rỗng thành công.
        Expanded(
          child: Obx(() {
            return FeatureStateView<List<ApprovalItemModel>>(
              state: controller.listState.value,
              onRetry: controller.loadApprovals,
              loadingBuilder: (_) =>
                  const Center(child: CircularProgressIndicator(color: Colors.blueAccent)),
              dataBuilder: (context, _, _) {
                final items = controller.filteredApprovals;
                if (items.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.task_alt_rounded, size: 56, color: Colors.green.shade400),
                        const SizedBox(height: 14),
                        const Text(
                          'Tuyệt vời! Không có yêu cầu nào đang chờ phê duyệt.',
                          style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Mọi hoạt động của AI Workforce đang vận hành an toàn trong hạn mức.',
                          style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.separated(
                  padding: const EdgeInsets.all(24),
                  itemCount: items.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 14),
                  itemBuilder: (ctx, i) {
                    final item = items[i];
                    return ApprovalTicketCard(item: item, controller: controller);
                  },
                );
              },
            );
          }),
        ),
      ],
    );
  }

  Widget _buildHistoryTab(BuildContext context) {
    return Obx(() {
      if (controller.historyApprovals.isEmpty) {
        return Center(
          child: Text('Chưa có lịch sử phê duyệt.', style: TextStyle(color: Colors.grey.shade500)),
        );
      }
      return ListView.separated(
        padding: const EdgeInsets.all(24),
        itemCount: controller.historyApprovals.length,
        separatorBuilder: (context, index) => const SizedBox(height: 10),
        itemBuilder: (ctx, i) {
          final item = controller.historyApprovals[i];
          return ApprovalHistoryItem(item: item);
        },
      );
    });
  }
}
