import 'package:flutter/material.dart';
import '../../../../../core/theme/app_theme.dart';
import '../../../../../core/theme/glassmorphism.dart';

class PestelGridWidget extends StatelessWidget {
  final List<dynamic> items;
  final bool isDesktop;
  final Function(String initialFactor) onAddFactor;
  final Function(dynamic item) onEditItem;
  final Function(String itemId) onDeleteItem;

  const PestelGridWidget({
    super.key,
    required this.items,
    required this.isDesktop,
    required this.onAddFactor,
    required this.onEditItem,
    required this.onDeleteItem,
  });

  @override
  Widget build(BuildContext context) {
    final factorOrder = ['Political', 'Economic', 'Social', 'Technological', 'Environmental', 'Legal'];
    final grouped = <String, List<dynamic>>{
      for (final f in factorOrder) f: <dynamic>[]
    };

    for (final item in items) {
      final rawFactor = item['factor']?.toString() ?? 'Political';
      final key = _normalizeFactorKey(rawFactor);
      if (grouped.containsKey(key)) {
        grouped[key]!.add(item);
      } else {
        grouped.putIfAbsent(key, () => []).add(item);
      }
    }

    final factorCards = factorOrder.map((fKey) {
      return _buildFactorGroupCard(context, fKey, grouped[fKey] ?? []);
    }).toList();

    if (!isDesktop) {
      return Column(
        children: factorCards.map((card) => Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: card,
        )).toList(),
      );
    }

    final leftCards = [factorCards[0], factorCards[2], factorCards[4]];
    final rightCards = [factorCards[1], factorCards[3], factorCards[5]];

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            children: leftCards.map((card) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: card,
            )).toList(),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            children: rightCards.map((card) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: card,
            )).toList(),
          ),
        ),
      ],
    );
  }

  String _normalizeFactorKey(String factor) {
    switch (factor.toUpperCase()) {
      case 'POLITICAL':
      case 'CHÍNH TRỊ':
        return 'Political';
      case 'ECONOMIC':
      case 'KINH TẾ':
        return 'Economic';
      case 'SOCIAL':
      case 'XÃ HỘI':
        return 'Social';
      case 'TECHNOLOGICAL':
      case 'CÔNG NGHỆ':
        return 'Technological';
      case 'ENVIRONMENTAL':
      case 'MÔI TRƯỜNG':
        return 'Environmental';
      case 'LEGAL':
      case 'PHÁP LÝ':
        return 'Legal';
      default:
        return 'Political';
    }
  }

  String _getPestelFactorLabel(String factor) {
    switch (factor.toUpperCase()) {
      case 'POLITICAL': return 'Chính trị';
      case 'ECONOMIC': return 'Kinh tế';
      case 'SOCIAL': return 'Xã hội';
      case 'TECHNOLOGICAL': return 'Công nghệ';
      case 'ENVIRONMENTAL': return 'Môi trường';
      case 'LEGAL': return 'Pháp lý';
      default: return factor;
    }
  }

  Color _getFactorColor(String factor) {
    switch (factor.toUpperCase()) {
      case 'POLITICAL': return const Color(0xFF3B82F6);
      case 'ECONOMIC': return const Color(0xFF10B981);
      case 'SOCIAL': return const Color(0xFFF59E0B);
      case 'TECHNOLOGICAL': return const Color(0xFF8B5CF6);
      case 'ENVIRONMENTAL': return const Color(0xFF06B6D4);
      case 'LEGAL': return const Color(0xFFEC4899);
      default: return AppTheme.primary;
    }
  }

  Widget _buildFactorGroupCard(BuildContext context, String factorKey, List<dynamic> factorItems) {
    final factorLabel = _getPestelFactorLabel(factorKey);
    final color = _getFactorColor(factorKey);

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
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: color,
                        boxShadow: [
                          BoxShadow(
                            color: color.withValues(alpha: 0.6),
                            blurRadius: 4,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      factorLabel,
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: color),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '${factorItems.length} mục',
                        style: const TextStyle(fontSize: 11, color: Colors.white70, fontWeight: FontWeight.w500),
                      ),
                    ),
                  ],
                ),
                InkWell(
                  onTap: () => onAddFactor(factorKey),
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
                        Text(
                          'Thêm mục',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(color: Colors.white12, height: 1),
            const SizedBox(height: 14),
            if (factorItems.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  'Chưa có nhận định cho yếu tố $factorLabel',
                  style: const TextStyle(fontSize: 12, color: Colors.white38, fontStyle: FontStyle.italic),
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: factorItems.length,
                separatorBuilder: (context, index) => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Divider(color: Colors.white10, height: 1),
                ),
                itemBuilder: (context, index) {
                  final item = factorItems[index];
                  final statement = item['statement']?.toString() ?? '';
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: color.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'Mục ${index + 1}',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color),
                            ),
                          ),
                          Row(
                            children: [
                              IconButton(
                                tooltip: 'Chỉnh sửa',
                                onPressed: () => onEditItem(item),
                                icon: const Icon(Icons.edit_outlined, size: 14, color: Colors.white60),
                                splashRadius: 14,
                                constraints: const BoxConstraints(),
                                padding: const EdgeInsets.all(4),
                              ),
                              const SizedBox(width: 4),
                              IconButton(
                                tooltip: 'Xóa',
                                onPressed: () => onDeleteItem(item['id'].toString()),
                                icon: const Icon(Icons.close_rounded, size: 14, color: Colors.white38),
                                splashRadius: 14,
                                constraints: const BoxConstraints(),
                                padding: const EdgeInsets.all(4),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
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
}
