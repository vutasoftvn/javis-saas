import 'package:flutter/material.dart';
import '../services/okr_weekly_generator_service.dart';

/// Hiện sau khi publish 1 Objective — hỏi founder có muốn tạo khung Operating
/// Cycle (weekly_plans rỗng) ngay không. Founder bỏ qua vẫn publish bình
/// thường (xem design doc mục 3 — generator không bắt buộc).
Future<void> showOkrWeeklyGeneratorDialog(
  BuildContext context, {
  required String objectiveId,
}) async {
  int durationWeeks = 12;
  final service = OkrWeeklyGeneratorService();

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setState) => AlertDialog(
        title: const Text('Tạo Operating Cycle cho Objective này?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Số tuần cho chu kỳ:'),
            Slider(
              value: durationWeeks.toDouble(),
              min: 1,
              max: 12,
              divisions: 11,
              label: '$durationWeeks tuần',
              onChanged: (v) => setState(() => durationWeeks = v.round()),
            ),
            Text('$durationWeeks tuần'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Bỏ qua'),
          ),
          ElevatedButton(
            onPressed: () async {
              try {
                await service.generate(objectiveId, durationWeeks);
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              } catch (e) {
                if (dialogContext.mounted) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    SnackBar(content: Text('Không tạo được cycle: $e')),
                  );
                }
              }
            },
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    ),
  );
}
