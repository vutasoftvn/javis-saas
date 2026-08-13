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
                  // Period Filter Bar (Ngày / Tuần / Tháng / Tất cả)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Khoảng thời gian thống kê',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textMutedDark,
                        ),
                      ),
                      _PeriodFilterBar(
                        selectedPeriod: controller.selectedPeriod.value,
                        onSelected: controller.setPeriod,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _StatCard(
                          title: controller.selectedPeriod.value == '1d'
                              ? 'Hôm nay (24h)'
                              : (controller.selectedPeriod.value == '7d'
                                  ? '7 ngày vừa qua'
                                  : (controller.selectedPeriod.value == 'all'
                                      ? 'Tổng chọn: Tất cả'
                                      : '30 ngày vừa qua')),
                          stats: controller.currentPeriodSummary,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _StatCard(
                          title: 'Tổng tích luỹ hệ thống',
                          stats: controller.allTime,
                        ),
                      ),
                    ],
                  ),

                  // OpenRouter Key Status Card or Notice
                  const SizedBox(height: 20),
                  if (controller.openRouterKeyInfo['configured'] == true)
                    _OpenRouterKeyCard(info: controller.openRouterKeyInfo)
                  else
                    const _OpenRouterUnconfiguredNotice(),

                  // OpenRouter Models Breakdown Card
                  if (controller.openRouterModels.isNotEmpty) ...[
                    const SizedBox(height: 24),
                    const Text(
                      'Chi tiết OpenRouter theo Model',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                    const SizedBox(height: 12),
                    ...controller.openRouterModels.entries.map((entry) {
                      final modelId = entry.key;
                      final mStats = entry.value as Map<String, dynamic>;
                      final totalOpenRouterCost = (controller.openRouterStats['cost_estimate'] as num?)?.toDouble() ?? 0.0;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _ModelUsageCard(
                          modelId: modelId,
                          stats: mStats,
                          totalProviderCost: totalOpenRouterCost,
                        ),
                      );
                    }),
                  ],
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

class _OpenRouterKeyCard extends StatelessWidget {
  final Map<String, dynamic> info;

  const _OpenRouterKeyCard({required this.info});

  @override
  Widget build(BuildContext context) {
    final label = info['label'] ?? 'OpenRouter Key';
    final limit = (info['limit'] as num?)?.toDouble();
    final keyUsage = (info['key_usage'] ?? info['usage'] as num?)?.toDouble();
    final usageDaily = (info['usage_daily'] as num?)?.toDouble();
    final usageWeekly = (info['usage_weekly'] as num?)?.toDouble();
    final usageMonthly = (info['usage_monthly'] as num?)?.toDouble();
    final accountUsage = (info['account_usage'] as num?)?.toDouble();
    final totalCredits = (info['total_credits'] as num?)?.toDouble();
    final balance = (info['balance'] ?? info['limit_remaining'] as num?)?.toDouble();
    final isFreeTier = info['is_free_tier'] == true;

    final accountProgress = (totalCredits != null && totalCredits > 0 && accountUsage != null)
        ? (accountUsage / totalCredits).clamp(0.0, 1.0)
        : 0.0;

    final isCustomKey = info['is_custom_workspace_key'] == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Card 1: Key Status & Header Info
        Glassmorphism(
          blur: 15,
          opacity: 0.2,
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.vpn_key_rounded, size: 20, color: AppTheme.primary),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Trạng thái OpenRouter API Key: $label',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textDark,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: (isCustomKey ? AppTheme.primary : Colors.cyan).withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: (isCustomKey ? AppTheme.primary : Colors.cyan).withValues(alpha: 0.3),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  isCustomKey ? Icons.lock_outline : Icons.cloud_done_outlined,
                                  size: 12,
                                  color: isCustomKey ? AppTheme.primary : Colors.cyan,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  isCustomKey ? '🔒 Đã lưu riêng Workspace (AES-256)' : '🌐 Đã lưu Workspace (Khoá mặc định hiện tại)',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: isCustomKey ? AppTheme.primary : Colors.cyan,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.primary,
                        side: const BorderSide(color: AppTheme.primary),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      icon: const Icon(Icons.key_outlined, size: 16),
                      label: Text(isCustomKey ? 'Đổi khoá' : 'Nhập khoá riêng'),
                      onPressed: () {
                        final controller = Get.find<UsageController>();
                        _showOpenRouterKeyDialog(context, controller);
                      },
                    ),
                    if (isCustomKey) ...[
                      const SizedBox(width: 8),
                      IconButton(
                        tooltip: 'Xoá khoá riêng, quay về mặc định',
                        icon: const Icon(Icons.delete_outline, color: AppTheme.error, size: 20),
                        onPressed: () async {
                          final controller = Get.find<UsageController>();
                          final ok = await controller.removeCustomOpenRouterKey();
                          if (ok) {
                            Get.snackbar('Đã xoá', 'Đã xoá khoá riêng, quay lại dùng khoá mặc định!');
                          }
                        },
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Card 2: Account Credits & Balance Summary Card
        Glassmorphism(
          blur: 15,
          opacity: 0.2,
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.account_balance_wallet_outlined, size: 16, color: AppTheme.primary),
                    SizedBox(width: 8),
                    Text(
                      'Thống kê toàn tài khoản OpenRouter',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final itemWidth = constraints.maxWidth > 500 ? (constraints.maxWidth - 32) / 3 : constraints.maxWidth;
                    return Wrap(
                      spacing: 16,
                      runSpacing: 12,
                      children: [
                        _BalanceMetricBox(
                          width: itemWidth,
                          icon: Icons.account_balance_wallet_rounded,
                          iconColor: AppTheme.primary,
                          label: 'Số dư tài khoản khả dụng',
                          value: balance != null ? '\$${balance.toStringAsFixed(4)}' : (isFreeTier ? 'Miễn phí' : 'Không giới hạn'),
                          isPrimary: true,
                        ),
                        if (totalCredits != null || limit != null)
                          _BalanceMetricBox(
                            width: itemWidth,
                            icon: Icons.add_card_rounded,
                            iconColor: Colors.blueAccent,
                            label: totalCredits != null ? 'Tổng nạp OpenRouter' : 'Hạn mức Key',
                            value: totalCredits != null ? '\$${totalCredits.toStringAsFixed(2)}' : '\$${limit!.toStringAsFixed(2)}',
                          ),
                        if (accountUsage != null)
                          _BalanceMetricBox(
                            width: itemWidth,
                            icon: Icons.shopping_cart_outlined,
                            iconColor: Colors.orangeAccent,
                            label: 'Đã tiêu (Toàn tài khoản)',
                            value: '\$${accountUsage.toStringAsFixed(4)}',
                          ),
                      ],
                    );
                  },
                ),
                if (totalCredits != null && accountUsage != null) ...[
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Tiến độ sử dụng nạp',
                        style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                      ),
                      Text(
                        '${(accountProgress * 100).toStringAsFixed(1)}% tổng nạp',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: accountProgress > 0.9 ? AppTheme.error : (accountProgress > 0.75 ? AppTheme.warning : AppTheme.primary),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: accountProgress,
                      minHeight: 8,
                      backgroundColor: Colors.white10,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        accountProgress > 0.9 ? AppTheme.error : (accountProgress > 0.75 ? AppTheme.warning : AppTheme.primary),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Card 3: Key Usage Breakdown Card
        Glassmorphism(
          blur: 15,
          opacity: 0.2,
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.timeline_rounded, size: 16, color: AppTheme.secondary),
                    SizedBox(width: 8),
                    Text(
                      'Tiêu thụ riêng của API Key hiện tại theo chu kỳ',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final itemWidth = constraints.maxWidth > 550 ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2;
                    return Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        if (usageDaily != null)
                          _MiniPeriodStatBox(width: itemWidth, label: 'Hôm nay (24h)', value: '\$${usageDaily.toStringAsFixed(4)}'),
                        if (usageWeekly != null)
                          _MiniPeriodStatBox(width: itemWidth, label: 'Tuần này (7d)', value: '\$${usageWeekly.toStringAsFixed(4)}'),
                        if (usageMonthly != null)
                          _MiniPeriodStatBox(width: itemWidth, label: 'Tháng này (30d)', value: '\$${usageMonthly.toStringAsFixed(4)}'),
                        if (keyUsage != null)
                          _MiniPeriodStatBox(width: itemWidth, label: 'Tích luỹ Key', value: '\$${keyUsage.toStringAsFixed(4)}'),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _BalanceMetricBox extends StatelessWidget {
  final double width;
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final bool isPrimary;

  const _BalanceMetricBox({
    required this.width,
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    this.isPrimary = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: isPrimary ? iconColor.withValues(alpha: 0.1) : Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isPrimary ? iconColor.withValues(alpha: 0.3) : Colors.white.withValues(alpha: 0.08),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: iconColor),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: isPrimary ? iconColor : AppTheme.textDark,
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniPeriodStatBox extends StatelessWidget {
  final double width;
  final String label;
  final String value;

  const _MiniPeriodStatBox({required this.width, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textDark)),
        ],
      ),
    );
  }
}

class _ModelUsageCard extends StatelessWidget {

  final String modelId;
  final Map<String, dynamic> stats;
  final double totalProviderCost;

  const _ModelUsageCard({
    required this.modelId,
    required this.stats,
    required this.totalProviderCost,
  });

  @override
  Widget build(BuildContext context) {
    final label = stats['label'] ?? modelId;
    final runs = stats['runs'] ?? 0;
    final inputTokens = stats['input_tokens'] ?? 0;
    final outputTokens = stats['output_tokens'] ?? 0;
    final totalTokens = inputTokens + outputTokens;
    final cost = (stats['cost_estimate'] as num?)?.toDouble() ?? 0.0;
    final ratio = totalProviderCost > 0 ? (cost / totalProviderCost).clamp(0.0, 1.0) : 0.0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.smart_toy_outlined, size: 14, color: AppTheme.primary),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    Text(
                      modelId,
                      style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    cost > 0 ? '\$${cost.toStringAsFixed(4)}' : '—',
                    style: const TextStyle(
                      color: AppTheme.textDark,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  Text(
                    '$runs lượt chat',
                    style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Vào: $inputTokens · Ra: $outputTokens token',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
              ),
              Text(
                'Tổng: $totalTokens',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: ratio > 0 ? ratio : 0.05,
              backgroundColor: AppTheme.surfaceDark,
              valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.primary),
              minHeight: 4,
            ),
          ),
        ],
      ),
    );
  }
}

class _PeriodFilterBar extends StatelessWidget {
  final String selectedPeriod;
  final ValueChanged<String> onSelected;

  const _PeriodFilterBar({
    required this.selectedPeriod,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final periods = [
      {'key': '1d', 'label': 'Ngày'},
      {'key': '7d', 'label': 'Tuần'},
      {'key': '30d', 'label': 'Tháng'},
      {'key': 'all', 'label': 'Tất cả'},
    ];

    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: periods.map((p) {
          final isSelected = selectedPeriod == p['key'];
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: InkWell(
              onTap: () => onSelected(p['key']!),
              borderRadius: BorderRadius.circular(8),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: isSelected ? AppTheme.primary : Colors.white.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  p['label']!,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                    color: isSelected ? Colors.black : Colors.white,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}


class _OpenRouterUnconfiguredNotice extends StatelessWidget {
  const _OpenRouterUnconfiguredNotice();

  @override
  Widget build(BuildContext context) {
    return Glassmorphism(
      blur: 15,
      opacity: 0.15,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.warning.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.key_off_outlined, color: AppTheme.warning, size: 20),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Chưa kết nối OpenRouter API Key',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.textDark,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Bạn có thể nhập OpenRouter API Key riêng của Workspace (mã hoá AES-256) hoặc cấu hình OPENROUTER_API_KEY trong .env trên máy chủ.',
                        style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.lock_outline, size: 18),
              label: const Text('Nhập OpenRouter API Key riêng (Mã hoá AES-256)', style: TextStyle(fontWeight: FontWeight.bold)),
              onPressed: () {
                final controller = Get.find<UsageController>();
                _showOpenRouterKeyDialog(context, controller);
              },
            ),
          ],
        ),
      ),
    );
  }
}

void _showOpenRouterKeyDialog(BuildContext context, UsageController controller) {
  final textController = TextEditingController();

  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Colors.white12),
      ),
      title: const Row(
        children: [
          Icon(Icons.lock_outline, color: AppTheme.primary, size: 20),
          SizedBox(width: 8),
          Text(
            'Nhập OpenRouter API Key',
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Khoá này sẽ được mã hoá 2 chiều AES-256 Fernet riêng theo Workspace trước khi lưu CSDL.',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: textController,
            obscureText: true,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            decoration: InputDecoration(
              hintText: 'sk-or-v1-...',
              hintStyle: const TextStyle(color: Colors.white38),
              filled: true,
              fillColor: Colors.white.withValues(alpha: 0.05),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Colors.white24),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppTheme.primary),
              ),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy', style: TextStyle(color: Colors.white54)),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          onPressed: () async {
            final key = textController.text.trim();
            if (key.isEmpty) return;
            Navigator.of(context).pop();
            final ok = await controller.saveCustomOpenRouterKey(key);
            if (ok) {
              Get.snackbar('Thành công', 'Đã mã hoá AES-256 và lưu OpenRouter API Key cho Workspace!');
            }
          },
          child: const Text('Lưu & Mã hoá', style: TextStyle(fontWeight: FontWeight.bold)),
        ),
      ],
    ),
  );
}




