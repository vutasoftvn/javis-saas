import 'package:flutter/material.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/modules/marketing/controllers/marketing_controller.dart';
import 'package:frontend/modules/marketing/views/widgets/marketing_common.dart';
import 'package:frontend/modules/marketing/views/widgets/marketing_forms.dart';

class MarketingLoopsSubtab extends StatelessWidget {
  final MarketingController controller;

  const MarketingLoopsSubtab({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    final loops = controller.loops;

    if (loops.isEmpty) {
      return MarketingEmpty(
        icon: Icons.loop_rounded,
        title: 'Chưa có vòng lặp tăng trưởng nào',
        subtitle:
            'Marketing OS v2 chuyển từ chiến dịch tuyến tính sang 4 Vòng lặp khép kín: Content Loop, Paid Ads Loop, Conversion Loop, Retention Loop (§18).',
        action: ElevatedButton.icon(
          onPressed: () => showLoopForm(context, controller),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Tạo vòng lặp mới'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      );
    }

    return Column(
      children: [
        MarketingTabActionBar(
          title: 'Vòng lặp Marketing khép kín (${loops.length})',
          actionLabel: 'Tạo vòng lặp',
          onAction: () => showLoopForm(context, controller),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: loops.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final loop = loops[index] as Map<String, dynamic>;
              final status = loop['status']?.toString() ?? 'active';
              final loopType = loop['loop_type']?.toString() ?? 'content';
              final lastRun = loop['last_run_at']?.toString();

              Color loopColor;
              String loopTypeLabel;
              switch (loopType) {
                case 'content':
                  loopColor = Colors.blueAccent;
                  loopTypeLabel = 'Content Loop';
                  break;
                case 'paid_ads':
                  loopColor = Colors.purpleAccent;
                  loopTypeLabel = 'Paid Ads Loop';
                  break;
                case 'conversion':
                  loopColor = Colors.amberAccent;
                  loopTypeLabel = 'Conversion Loop';
                  break;
                case 'retention':
                  loopColor = AppTheme.success;
                  loopTypeLabel = 'Retention Loop';
                  break;
                default:
                  loopColor = AppTheme.primaryLight;
                  loopTypeLabel = loopType;
              }

              return MarketingCard(
                borderColor: loopColor.withValues(alpha: 0.3),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.sync_rounded, color: loopColor, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            loop['name']?.toString() ?? '',
                            style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14.5),
                          ),
                        ),
                        MarketingChip(label: loopTypeLabel, color: loopColor),
                        const SizedBox(width: 6),
                        MarketingChip(
                          label: status == 'active' ? 'Đang chạy' : 'Tạm dừng',
                          color: status == 'active' ? AppTheme.success : AppTheme.textMutedDark,
                        ),
                      ],
                    ),
                    if ((loop['description']?.toString() ?? '').isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        loop['description'].toString(),
                        style: const TextStyle(fontSize: 12.5, color: Colors.white70, height: 1.4),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Text(
                          'Tần suất: ${loop['loop_config']?['frequency'] ?? 'Hàng tuần'} · '
                          'Chạy gần nhất: ${lastRun != null ? formatDate(lastRun) : 'Chưa chạy lần nào'}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                        ),
                        const Spacer(),
                        ElevatedButton.icon(
                          onPressed: () => controller.triggerLoop(loop['id'].toString()),
                          icon: const Icon(Icons.play_arrow_rounded, size: 16),
                          label: const Text('Kích hoạt chu kỳ', style: TextStyle(fontSize: 12)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: loopColor,
                            foregroundColor: const Color(0xFF04070E),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          ),
                        ),
                        const SizedBox(width: 6),
                        IconButton(
                          tooltip: 'Sửa',
                          icon: const Icon(Icons.edit_outlined, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => showLoopForm(context, controller, existing: loop),
                        ),
                        IconButton(
                          tooltip: 'Xoá',
                          icon: const Icon(Icons.delete_outline, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => confirmMarketingDelete(
                            context,
                            'Xoá vòng lặp?',
                            loop['name']?.toString() ?? '',
                            () => controller.deleteLoop(loop['id'].toString()),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
