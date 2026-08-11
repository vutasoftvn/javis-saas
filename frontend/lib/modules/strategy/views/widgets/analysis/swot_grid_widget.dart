import 'package:flutter/material.dart';
import '../../../../../core/theme/app_theme.dart';
import '../../../../../core/theme/glassmorphism.dart';
import 'analysis_common_widgets.dart';

class SwotGridWidget extends StatelessWidget {
  final List<dynamic> items;
  final bool isDesktop;
  final Function(String initialCategory) onAddCategory;
  final Function(dynamic item) onEditItem;
  final Function(String itemId) onDeleteItem;

  const SwotGridWidget({
    super.key,
    required this.items,
    required this.isDesktop,
    required this.onAddCategory,
    required this.onEditItem,
    required this.onDeleteItem,
  });

  @override
  Widget build(BuildContext context) {
    final categories = ['Strength', 'Weakness', 'Opportunity', 'Threat'];
    final grouped = <String, List<dynamic>>{
      for (final c in categories) c: <dynamic>[]
    };

    for (final item in items) {
      final rawCat = item['category']?.toString() ?? 'Strength';
      final key = _normalizeSwotCategory(rawCat);
      grouped[key]?.add(item);
    }

    final categoryCards = categories.map((catKey) {
      return _buildCategoryCard(context, catKey, grouped[catKey] ?? []);
    }).toList();

    if (!isDesktop) {
      return Column(
        children: categoryCards.map((card) => Padding(
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
            Expanded(child: categoryCards[0]),
            const SizedBox(width: 16),
            Expanded(child: categoryCards[1]),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: categoryCards[2]),
            const SizedBox(width: 16),
            Expanded(child: categoryCards[3]),
          ],
        ),
      ],
    );
  }

  String _normalizeSwotCategory(String cat) {
    switch (cat.toUpperCase()) {
      case 'STRENGTH':
      case 'STRENGTHS':
      case 'ĐIỂM MẠNH':
        return 'Strength';
      case 'WEAKNESS':
      case 'WEAKNESSES':
      case 'ĐIỂM YẾU':
        return 'Weakness';
      case 'OPPORTUNITY':
      case 'OPPORTUNITIES':
      case 'CƠ HỘI':
        return 'Opportunity';
      case 'THREAT':
      case 'THREATS':
      case 'THÁCH THỨC':
        return 'Threat';
      default:
        return 'Strength';
    }
  }

  Widget _buildCategoryCard(BuildContext context, String catKey, List<dynamic> catItems) {
    final catLabel = getSwotCategoryLabel(catKey);
    final color = getSwotCategoryColor(catKey);

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
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
                    ),
                    const SizedBox(width: 8),
                    Text(catLabel, style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: color)),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text('${catItems.length} mục', style: const TextStyle(fontSize: 11, color: Colors.white70)),
                    ),
                  ],
                ),
                InkWell(
                  onTap: () => onAddCategory(catKey),
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
                        Text('Thêm mục', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(color: Colors.white12, height: 1),
            const SizedBox(height: 14),
            if (catItems.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text('Chưa có mục cho $catLabel', style: const TextStyle(fontSize: 12, color: Colors.white38, fontStyle: FontStyle.italic)),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: catItems.length,
                separatorBuilder: (context, index) => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Divider(color: Colors.white10, height: 1),
                ),
                itemBuilder: (context, index) {
                  final item = catItems[index];
                  final statement = item['statement']?.toString() ?? '';
                  final impact = item['impact']?.toString() ?? 'High';
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Text('Mục ${index + 1}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color)),
                              const SizedBox(width: 8),
                              AnalysisBadge(text: impact, color: _getImpactColor(impact)),
                            ],
                          ),
                          Row(
                            children: [
                              IconButton(
                                onPressed: () => onEditItem(item),
                                icon: const Icon(Icons.edit_outlined, size: 14, color: Colors.white60),
                              ),
                              IconButton(
                                onPressed: () => onDeleteItem(item['id'].toString()),
                                icon: const Icon(Icons.close_rounded, size: 14, color: Colors.white38),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        statement,
                        style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.9), height: 1.4),
                      ),
                    ],
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  Color _getImpactColor(String impact) {
    switch (impact.toUpperCase()) {
      case 'HIGH': return Colors.greenAccent;
      case 'MEDIUM': return Colors.blueAccent;
      case 'LOW': return Colors.redAccent;
      default: return Colors.white70;
    }
  }
}
