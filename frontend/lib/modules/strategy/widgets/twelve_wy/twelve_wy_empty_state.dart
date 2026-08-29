import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class TwelveWyEmptyState extends StatelessWidget {
  final VoidCallback onCreatePlan;

  const TwelveWyEmptyState({super.key, required this.onCreatePlan});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 40),
        padding: const EdgeInsets.all(32),
        constraints: const BoxConstraints(maxWidth: 520),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.secondary.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.calendar_month_rounded, size: 36, color: AppTheme.secondary),
            ),
            const SizedBox(height: 16),
            const Text(
              'Chưa có Kế hoạch Tuần nào',
              style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Bạn có thể kích hoạt từ Lộ trình MVP để tự động phân bổ kế hoạch các tuần, hoặc tạo tuần thực thi đầu tiên (mặc định bắt đầu từ Thứ Hai).',
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.4),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: onCreatePlan,
              icon: const Icon(Icons.add_rounded, size: 16),
              label: const Text('Tạo Kế hoạch Tuần 1'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.secondary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
