import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

/// Node 4: Gate Phê duyệt An toàn (Human-in-the-loop)
class MarketingNode4ApprovalsTab extends GetView<MarketingController> {
  const MarketingNode4ApprovalsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final approvals = controller.pendingApprovals;

      if (approvals.isEmpty) {
        return const MarketingEmpty(
          icon: Icons.verified_outlined,
          title: 'Không có hành động nào chờ duyệt',
          subtitle:
              'Nghiên cứu, soạn nháp, phân tích và đề xuất được chạy tự động. Xuất bản nội dung, gửi email hàng '
              'loạt, chi ngân sách hay đổi giá luôn dừng lại ở đây để bạn quyết định.',
        );
      }

      return Column(
        children: [
          MarketingCard(
            child: MarketingSectionHeader(
              title: 'Hàng đợi phê duyệt (${approvals.length})',
              description: 'Sau khi bạn phê duyệt, hành động mới được thực thi và ghi vào nhật ký.',
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: ListView.separated(
              itemCount: approvals.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, index) => _buildApprovalRow(context, approvals[index] as Map<String, dynamic>),
            ),
          ),
        ],
      );
    });
  }

  Widget _buildApprovalRow(BuildContext context, Map<String, dynamic> a) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: MarketingCard(
        borderColor: Colors.amberAccent.withValues(alpha: 0.3),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    a['title']?.toString() ?? 'Hành động cần phê duyệt',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13.5),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    'Loại: ${a['action_type']} · Đề xuất bởi: ${a['requested_by_agent'] ?? '—'} · ${formatDate(a['created_at']?.toString())}',
                    style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                  ),
                ],
              ),
            ),
            TextButton.icon(
              onPressed: () => showApprovalReviewDialog(context, controller, a, approve: true),
              icon: const Icon(Icons.check_circle_outline, size: 16),
              label: const Text('Duyệt', style: TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(foregroundColor: AppTheme.success),
            ),
            TextButton.icon(
              onPressed: () => showApprovalReviewDialog(context, controller, a, approve: false),
              icon: const Icon(Icons.cancel_outlined, size: 16),
              label: const Text('Từ chối', style: TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(foregroundColor: AppTheme.accent),
            ),
          ],
        ),
      ),
    );
  }
}
