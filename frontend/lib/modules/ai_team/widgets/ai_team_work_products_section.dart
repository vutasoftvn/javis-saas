import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamWorkProductsSection extends StatelessWidget {
  final AiTeamController controller;

  const AiTeamWorkProductsSection({
    super.key,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.inventory_2_rounded,
                  color: AppTheme.primary, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Sản Phẩm Bàn Giao Gần Đây (Work Products)',
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: AppTheme.textDark),
              ),
              const Spacer(),
              Text(
                '${controller.workProducts.length} sản phẩm',
                style: const TextStyle(
                    fontSize: 12, color: AppTheme.textMutedDark),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: controller.workProducts.take(5).length,
            separatorBuilder: (context, index) =>
                const Divider(color: AppTheme.borderDark, height: 16),
            itemBuilder: (context, index) {
              final wp = controller.workProducts[index];
              final wpId = wp['id'] as int? ?? 0;
              final title = wp['title'] ?? 'Sản phẩm bàn giao';
              final type = wp['product_type'] ?? 'DOCUMENT';
              final status = wp['status'] ?? 'DRAFT';
              final summary = wp['executive_summary'] ?? 'Không có tóm tắt.';
              final isDraft = status == 'DRAFT';

              return Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDarkLighter,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.description_outlined,
                        size: 18, color: AppTheme.primary),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              title,
                              style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                  color: AppTheme.textDark),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: isDraft
                                    ? AppTheme.warning.withValues(alpha: 0.15)
                                    : AppTheme.success.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                isDraft
                                    ? 'Bản nháp'
                                    : (status == 'ACCEPTED'
                                        ? 'Đã duyệt'
                                        : status),
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  color: isDraft
                                      ? AppTheme.warning
                                      : AppTheme.success,
                                ),
                              ),
                            ),
                          ],
                        ),
                        Text(
                          'Loại: $type · $summary',
                          style: const TextStyle(
                              fontSize: 11, color: AppTheme.textMutedDark),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  if (isDraft) ...[
                    const SizedBox(width: 8),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        minimumSize: Size.zero,
                      ),
                      onPressed: () => controller.acceptProduct(wpId),
                      icon: const Icon(Icons.check_circle_outline, size: 14),
                      label: const Text('Nghiệm thu',
                          style: TextStyle(
                              fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
