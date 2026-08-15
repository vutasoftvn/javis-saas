import 'package:flutter/material.dart';

/// Card Tóm Tắt Bản Nháp Chu Kỳ Trong Khung Chat (In-Chat Strategic Draft & Approval Card)
/// Hiển thị ngay dưới câu lệnh đối thoại để Founder xem nhanh và bấm Duyệt/Kích hoạt.
class StrategicDraftCard extends StatelessWidget {
  final String projectName;
  final int durationWeeks;
  final String theme;
  final List<String>? weekHighlights;
  final VoidCallback? onApprove;
  final VoidCallback? onEditRequest;

  const StrategicDraftCard({
    super.key,
    required this.projectName,
    required this.durationWeeks,
    required this.theme,
    this.weekHighlights,
    this.onApprove,
    this.onEditRequest,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: const Color(0xFF38BDF8).withValues(alpha: 0.4),
          width: 1.2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header Badge
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.assignment_turned_in_outlined,
                  size: 16,
                  color: Color(0xFF38BDF8),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'BẢN NHÁP CHU KỲ $durationWeeks TUẦN',
                      style: const TextStyle(
                        color: Color(0xFF38BDF8),
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                      ),
                    ),
                    Text(
                      projectName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (theme.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Trọng tâm: $theme',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
            ),
          ],
          const SizedBox(height: 10),
          const Divider(height: 1, color: Color(0xFF334155)),
          const SizedBox(height: 10),

          // Action Buttons
          Row(
            children: [
              if (onApprove != null)
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: onApprove,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    icon: const Icon(Icons.check_circle_outline, size: 16),
                    label: const Text(
                      'Duyệt & Kích hoạt',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              if (onApprove != null && onEditRequest != null)
                const SizedBox(width: 8),
              if (onEditRequest != null)
                OutlinedButton.icon(
                  onPressed: onEditRequest,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF94A3B8),
                    side: const BorderSide(color: Color(0xFF475569)),
                    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  icon: const Icon(Icons.edit_note, size: 16),
                  label: const Text(
                    'Sửa số tuần',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
