import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/usage_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/floating_app_bar.dart';

class UsageView extends GetView<UsageController> {
  const UsageView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<UsageController>()) {
      Get.put(UsageController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Top Floating AppBar Card
          JavisFloatingAppBar(
            title: 'Sử dụng & chi phí',
            subtitle: 'Thống kê lượng token và chi phí API theo chu kỳ',
            icon: Icons.bar_chart_rounded,
            actions: [
              Obx(
                () => IconButton(
                  icon: const Icon(Icons.refresh, color: AppTheme.primary),
                  tooltip: 'Tải lại',
                  onPressed: controller.isLoading.value ? null : controller.loadUsage,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.summary.value == null) {
                return const Center(child: CircularProgressIndicator());
              }
              if (controller.summary.value == null) {
                return const EmptyState(
                  icon: Icons.bar_chart_outlined,
                  title: 'Chưa có dữ liệu sử dụng',
                  subtitle: 'Số liệu sẽ xuất hiện sau khi có cuộc trò chuyện hoàn tất.',
                );
              }

              return ListView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: _StatCard(
                          title: '30 ngày gần đây',
                          stats: controller.rolling30d,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _StatCard(
                          title: 'Tổng tích luỹ',
                          stats: controller.allTime,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Theo provider',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textMutedDark,
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (controller.byProvider.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 8),
                      child: Text(
                        'Chưa có run nào hoàn tất.',
                        style: TextStyle(color: AppTheme.textMutedDark),
                      ),
                    )
                  else
                    ...controller.byProvider.entries.map(
                      (entry) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _ProviderRow(
                          provider: entry.key,
                          stats: entry.value as Map<String, dynamic>,
                        ),
                      ),
                    ),
                ],
              );
            }),
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final Map<String, dynamic> stats;

  const _StatCard({required this.title, required this.stats});

  @override
  Widget build(BuildContext context) {
    final runs = stats['runs'] ?? 0;
    final inputTokens = stats['input_tokens'] ?? 0;
    final outputTokens = stats['output_tokens'] ?? 0;
    final cost = (stats['cost_estimate'] as num?)?.toDouble() ?? 0.0;

    return Glassmorphism(
      blur: 15,
      opacity: 0.2,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 12),
            Text(
              '$runs lượt trả lời',
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '$inputTokens vào · $outputTokens ra token',
              style: const TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 4),
            Text(
              cost > 0 ? '\$${cost.toStringAsFixed(4)}' : 'Chưa có chi phí ghi nhận',
              style: const TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProviderRow extends StatelessWidget {
  final String provider;
  final Map<String, dynamic> stats;

  const _ProviderRow({required this.provider, required this.stats});

  @override
  Widget build(BuildContext context) {
    final runs = stats['runs'] ?? 0;
    final cost = (stats['cost_estimate'] as num?)?.toDouble() ?? 0.0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: AppTheme.secondary,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              provider,
              style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600),
            ),
          ),
          Text(
            '$runs lượt',
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
          const SizedBox(width: 16),
          Text(
            cost > 0 ? '\$${cost.toStringAsFixed(4)}' : '—',
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
