import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/tech_radar_controller.dart';

class RadarItemDetailDialog extends StatelessWidget {
  final Map<String, dynamic> item;

  const RadarItemDetailDialog({super.key, required this.item});

  static void show(BuildContext context, Map<String, dynamic> item) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (context) => RadarItemDetailDialog(item: item),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<TechRadarController>();
    final name = item['name']?.toString() ?? 'Công nghệ';
    final category = item['category']?.toString() ?? 'Chung';
    final status = (item['status']?.toString() ?? 'WATCH').toUpperCase();
    final maturity = item['maturity']?.toString() ?? 'beta';
    final potential = item['potential']?.toString() ?? 'high';
    final cosaUse = item['cosa_use']?.toString() ?? 'pattern';
    final integration = item['integration']?.toString() ?? 'no';
    final description = item['description']?.toString() ?? 'Chưa có mô tả chi tiết.';
    final lastReviewed = item['last_reviewed']?.toString() ?? 'N/A';
    final itemId = item['id']?.toString() ?? '';

    Color statusColor = const Color(0xFFA855F7);
    if (status == 'ADOPT') statusColor = const Color(0xFF10B981);
    if (status == 'TRIAL') statusColor = const Color(0xFF00E5FF);
    if (status == 'ASSESS') statusColor = const Color(0xFFF59E0B);

    return Dialog(
      backgroundColor: const Color(0xFF090E1B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: statusColor.withValues(alpha: 0.35),
          width: 1.5,
        ),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Container(
        width: 600,
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    Icons.radar_rounded,
                    color: statusColor,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        category,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                  ),
                  child: Text(
                    status,
                    style: TextStyle(
                      color: statusColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Metadata Grid
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF131B2E),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      _buildMetaField('Độ chín muồi', maturity.toUpperCase(), const Color(0xFF38BDF8)),
                      _buildMetaField('Tiềm năng', potential.toUpperCase(), const Color(0xFFFBBF24)),
                      _buildMetaField('COSA Role', cosaUse.toUpperCase(), const Color(0xFFA78BFA)),
                      _buildMetaField('Integration', integration.toUpperCase(), const Color(0xFF34D399)),
                    ],
                  ),
                  const Divider(color: Color(0xFF1E293B), height: 24),
                  Row(
                    children: [
                      const Text(
                        'Đánh giá gần nhất:',
                        style: TextStyle(color: Color(0xFF64748B), fontSize: 11),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        lastReviewed,
                        style: const TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Description
            const Text(
              'Mô tả & Kiến trúc ứng dụng trong COSA OS:',
              style: TextStyle(
                color: Color(0xFF94A3B8),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
              ),
              child: Text(
                description,
                style: const TextStyle(
                  color: Color(0xFFCBD5E1),
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Quick Status Actions
            Row(
              children: [
                const Text(
                  'Chuyển trạng thái:',
                  style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                ),
                const SizedBox(width: 10),
                ...['ADOPT', 'TRIAL', 'ASSESS', 'WATCH'].map((st) {
                  final isSelected = st == status;
                  return Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        side: BorderSide(
                          color: isSelected ? statusColor : const Color(0xFF334155),
                        ),
                        backgroundColor: isSelected ? statusColor.withValues(alpha: 0.15) : Colors.transparent,
                      ),
                      onPressed: () {
                        controller.updateItemStatus(itemId, st);
                        Navigator.of(context).pop();
                      },
                      child: Text(
                        st,
                        style: TextStyle(
                          color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetaField(String label, String value, Color accent) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10)),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(color: accent, fontSize: 12, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}
