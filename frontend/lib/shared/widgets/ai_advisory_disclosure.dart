import 'package:flutter/material.dart';

class AiAdvisoryDisclosure extends StatelessWidget {
  final String domain;
  final bool hasDataWarning;
  final VoidCallback? onReportProblem;

  const AiAdvisoryDisclosure({
    super.key,
    required this.domain,
    this.hasDataWarning = true,
    this.onReportProblem,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF3B82F6).withValues(alpha: 0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: Color(0xFF38BDF8), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Thông tin do AI tạo chỉ mang tính tham khảo (${domain.toUpperCase()}). Cần có chuyên viên pháp chế/luật sư rà soát trước khi quyết định.',
                  style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 12),
                ),
                if (hasDataWarning) ...[
                  const SizedBox(height: 4),
                  const Text(
                    'Cảnh báo: Không nhập dữ liệu cá nhân nhạy cảm, bí mật kinh doanh chưa mã hoá.',
                    style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                  ),
                ],
              ],
            ),
          ),
          if (onReportProblem != null) ...[
            const SizedBox(width: 8),
            TextButton(
              onPressed: onReportProblem,
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text(
                'Báo cáo',
                style: TextStyle(color: Color(0xFFF87171), fontSize: 12),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
