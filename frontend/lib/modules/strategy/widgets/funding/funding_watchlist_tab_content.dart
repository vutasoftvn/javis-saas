import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class FundingWatchlistTabContent extends StatelessWidget {
  final List<dynamic> draftWatchlist;

  const FundingWatchlistTabContent({super.key, required this.draftWatchlist});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.blueGrey.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blueGrey.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: const [
                Icon(Icons.visibility_outlined, color: Colors.cyanAccent, size: 22),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Danh mục 5 Chương trình Quốc gia Dự thảo giai đoạn 2026–2035 đang lấy ý kiến. '
                    'COSA chỉ theo dõi tiến độ ban hành, không tính vào kế hoạch tài trợ hiện hành của Project.',
                    style: TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (draftWatchlist.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: const Center(
                child: Text('Không có chương trình dự thảo nào đang theo dõi.', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
              ),
            )
          else
            ...draftWatchlist.map((p) => _buildWatchlistCard(p as Map<String, dynamic>)),
        ],
      ),
    );
  }

  Widget _buildWatchlistCard(Map<String, dynamic> program) {
    final name = program['name'] ?? 'Chương trình dự thảo';
    final authority = program['authority'] ?? 'Cơ quan quản lý';
    final summary = program['summary'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(name, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.grey.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: Colors.grey.withValues(alpha: 0.4)),
                ),
                child: const Text('DỰ THẢO THEO DÕI', style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(authority, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ],
        ],
      ),
    );
  }
}
