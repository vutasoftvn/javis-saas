import 'package:flutter/material.dart';
import '../../../data/models/company_pulse_model.dart';

class Top3FocusWidget extends StatelessWidget {
  final List<NextBestActionModel> actions;
  final Function(NextBestActionModel) onActionTap;

  const Top3FocusWidget({
    super.key,
    required this.actions,
    required this.onActionTap,
  });

  @override
  Widget build(BuildContext context) {
    if (actions.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B).withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF334155)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.stars_outlined, color: Color(0xFFF59E0B), size: 20),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'TOP 3 TRỌNG TÂM HÔM NAY (12-Week Year Focus)',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      letterSpacing: 0.5,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Chưa có hành động ưu tiên nào được sinh ra cho dự án. Hãy bắt đầu bằng việc thiết lập các giả định quan trọng của giai đoạn P1 (Problem Validation) hoặc kích hoạt chu trình 12 tuần.',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.stars, color: Color(0xFFF59E0B), size: 20),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'TOP 3 TRỌNG TÂM HÔM NAY (12-Week Year Focus)',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 0.5,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text(
                'Next Best Actions',
                style: TextStyle(fontSize: 11, color: Color(0xFF60A5FA), fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ...actions.asMap().entries.map((entry) {
          final idx = entry.key + 1;
          final item = entry.value;
          return _buildActionCard(idx, item);
        }),
      ],
    );
  }

  Widget _buildActionCard(int index, NextBestActionModel item) {
    Color tagColor;
    String tagLabel = item.category;

    switch (item.category) {
      case 'DECISION':
        tagColor = const Color(0xFFF59E0B);
        tagLabel = 'Quyết định';
        break;
      case 'EXPERIMENT':
        tagColor = const Color(0xFFEC4899);
        tagLabel = 'Thực nghiệm';
        break;
      case 'MISSION':
        tagColor = const Color(0xFF8B5CF6);
        tagLabel = 'Mission';
        break;
      default:
        tagColor = const Color(0xFF10B981);
        tagLabel = 'Hành động';
    }

    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFF334155), width: 1),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => onActionTap(item),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  shape: BoxShape.circle,
                  border: Border.all(color: const Color(0xFF475569)),
                ),
                child: Text(
                  '$index',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: tagColor.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            tagLabel,
                            style: TextStyle(fontSize: 10, color: tagColor, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            item.domain,
                            style: TextStyle(fontSize: 10, color: Colors.white.withValues(alpha: 0.4), fontWeight: FontWeight.w500),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      item.title,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      item.rationale,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.white.withValues(alpha: 0.65),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.arrow_forward_ios, color: Color(0xFF64748B), size: 14),
            ],
          ),
        ),
      ),
    );
  }
}
