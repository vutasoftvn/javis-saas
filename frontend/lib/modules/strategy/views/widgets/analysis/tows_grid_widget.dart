import 'package:flutter/material.dart';
import '../../../../../core/theme/app_theme.dart';
import '../../../../../core/theme/glassmorphism.dart';
import 'analysis_common_widgets.dart';

class TowsGridWidget extends StatelessWidget {
  final List<dynamic> options;
  final bool isDesktop;
  final Function(String initialQuadrant) onAddQuadrant;
  final Function(dynamic option) onEditOption;
  final Function(String optionId) onDeleteOption;

  const TowsGridWidget({
    super.key,
    required this.options,
    required this.isDesktop,
    required this.onAddQuadrant,
    required this.onEditOption,
    required this.onDeleteOption,
  });

  @override
  Widget build(BuildContext context) {
    final quadrants = ['SO', 'ST', 'WO', 'WT'];
    final grouped = <String, List<dynamic>>{
      for (final q in quadrants) q: <dynamic>[]
    };

    for (final opt in options) {
      final qKey = (opt['quadrant']?.toString() ?? 'SO').toUpperCase();
      grouped[qKey]?.add(opt);
    }

    final quadCards = quadrants.map((qKey) {
      return _buildQuadrantCard(context, qKey, grouped[qKey] ?? []);
    }).toList();

    if (!isDesktop) {
      return Column(
        children: quadCards.map((card) => Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: card,
        )).toList(),
      );
    }

    return Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: quadCards[0]),
            const SizedBox(width: 16),
            Expanded(child: quadCards[1]),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: quadCards[2]),
            const SizedBox(width: 16),
            Expanded(child: quadCards[3]),
          ],
        ),
      ],
    );
  }

  Widget _buildQuadrantCard(BuildContext context, String qKey, List<dynamic> qItems) {
    final label = getTowsQuadrantLabel(qKey);
    final color = getTowsQuadrantColor(qKey);

    return Glassmorphism(
      blur: 10,
      opacity: 0.12,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark.withValues(alpha: 0.45),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
                    const SizedBox(width: 8),
                    Text(label, style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: color)),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text('${qItems.length} chiến lược', style: const TextStyle(fontSize: 11, color: Colors.white70)),
                    ),
                  ],
                ),
                InkWell(
                  onTap: () => onAddQuadrant(qKey),
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: color.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.add_rounded, size: 14, color: color),
                        const SizedBox(width: 4),
                        Text('Thêm', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(color: Colors.white12, height: 1),
            const SizedBox(height: 14),
            if (qItems.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text('Chưa có lựa chọn chiến lược cho $qKey', style: const TextStyle(fontSize: 12, color: Colors.white38, fontStyle: FontStyle.italic)),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: qItems.length,
                separatorBuilder: (context, index) => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Divider(color: Colors.white10, height: 1),
                ),
                itemBuilder: (context, index) {
                  final item = qItems[index];
                  final title = item['title']?.toString() ?? '';
                  final tradeoffs = item['tradeoffs']?.toString() ?? '';
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
                            ),
                          ),
                          Row(
                            children: [
                              IconButton(
                                onPressed: () => onEditOption(item),
                                icon: const Icon(Icons.edit_outlined, size: 14, color: Colors.white60),
                              ),
                              IconButton(
                                onPressed: () => onDeleteOption(item['id'].toString()),
                                icon: const Icon(Icons.close_rounded, size: 14, color: Colors.white38),
                              ),
                            ],
                          ),
                        ],
                      ),
                      if (tradeoffs.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Sự đánh đổi: $tradeoffs',
                          style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.7), fontStyle: FontStyle.italic),
                        ),
                      ],
                    ],
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
