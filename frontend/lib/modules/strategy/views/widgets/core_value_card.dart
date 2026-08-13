import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/glassmorphism.dart';

/// Đúng 3 slot cố định (§4.1: "đúng ba, đánh số 1-3") - widget này KHÔNG có nút
/// thêm/xoá, vị trí slot_no luôn hiển thị kể cả khi rỗng, để UI không bao giờ
/// cho tạo được Core Value thứ 4.
class CoreValueCard extends StatelessWidget {
  final int slotNo;
  final TextEditingController titleController;
  final TextEditingController descriptionController;
  final TextEditingController decisionRuleController;
  final bool readOnly;

  const CoreValueCard({
    super.key,
    required this.slotNo,
    required this.titleController,
    required this.descriptionController,
    required this.decisionRuleController,
    this.readOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    return Glassmorphism(
      blur: 10,
      opacity: 0.12,
      color: AppTheme.primary,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Container(
                  width: 24,
                  height: 24,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.25),
                    shape: BoxShape.circle,
                  ),
                  child: Text('$slotNo', style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 8),
                Text('Giá trị cốt lõi $slotNo', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14)),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Tên giá trị',
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: titleController,
              readOnly: readOnly,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: const InputDecoration(
                hintText: 'Nhập tên giá trị cốt lõi...',
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
            ),
            const SizedBox(height: 14),
            const Text(
              'Mô tả',
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: descriptionController,
              readOnly: readOnly,
              maxLines: 2,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: const InputDecoration(
                hintText: 'Nhập mô tả chi tiết...',
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
            ),
            const SizedBox(height: 14),
            const Text(
              'Decision rule (câu kiểm tra khi ra quyết định)',
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: decisionRuleController,
              readOnly: readOnly,
              maxLines: 2,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: const InputDecoration(
                hintText: 'Quy tắc / tiêu chí tự kiểm tra khi ra quyết định...',
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
