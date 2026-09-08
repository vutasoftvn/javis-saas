import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../data/models/strategy_lens_model.dart';
import '../../../../data/models/evidence_model.dart';

class SwotEvidenceGridWidget extends StatelessWidget {
  final List<SwotItemModel> swotItems;
  final List<EvidenceModel> evidences;
  final Function(SwotType category, String statement, double importance, List<int> evidenceRefs) onCreateSwotItem;

  const SwotEvidenceGridWidget({
    super.key,
    required this.swotItems,
    required this.evidences,
    required this.onCreateSwotItem,
  });

  void _showAddSwotDialog(BuildContext context, SwotType initialCategory) {
    final statementCtrl = TextEditingController();
    SwotType selectedCategory = initialCategory;
    double importance = 0.8;
    List<int> selectedEvidenceIds = [];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          final isStrengthOrWeakness = (selectedCategory == SwotType.strength || selectedCategory == SwotType.weakness);

          return AlertDialog(
            backgroundColor: const Color(0xFF0F172A),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: selectedCategory.color, width: 1.5),
            ),
            title: Row(
              children: [
                Icon(Icons.grid_view_rounded, color: selectedCategory.color, size: 20),
                const SizedBox(width: 8),
                Text(
                  L10nKey.swotAddTitle.tr,
                  style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            content: SizedBox(
              width: 480,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    DropdownButtonFormField<SwotType>(
                      initialValue: selectedCategory,
                      dropdownColor: const Color(0xFF1E293B),
                      decoration: InputDecoration(
                        labelText: L10nKey.swotTypeLabel.tr,
                        labelStyle: const TextStyle(color: Colors.white70),
                      ),
                      items: SwotType.values.map((c) {
                        return DropdownMenuItem(
                          value: c,
                          child: Text(c.localizedLabel, style: TextStyle(color: c.color, fontWeight: FontWeight.bold)),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) setState(() => selectedCategory = val);
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: statementCtrl,
                      maxLines: 2,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: L10nKey.swotContentLabel.tr,
                        labelStyle: const TextStyle(color: Colors.white70),
                        hintText: selectedCategory == SwotType.strength
                            ? L10nKey.swotContentHint.tr
                            : '...',
                        hintStyle: const TextStyle(color: Colors.white30, fontSize: 12),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Evidence Selection for S & W (Mandatory)
                    if (isStrengthOrWeakness) ...[
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444).withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.3)),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.shield_outlined, color: Color(0xFFEF4444), size: 16),
                            SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'Quy tắc COSA: Điểm Mạnh và Điểm Yếu BẮT BUỘC phải trích dẫn Bằng chứng thực tế.',
                                style: TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Chọn Bằng Chứng Minh Chứng:',
                        style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        height: 120,
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: evidences.isEmpty
                            ? const Center(
                                child: Text('Chưa có bằng chứng nào trong kho', style: TextStyle(color: Colors.white38, fontSize: 11)),
                              )
                            : ListView.builder(
                                itemCount: evidences.length,
                                itemBuilder: (context, eIdx) {
                                  final ev = evidences[eIdx];
                                  final isSelected = selectedEvidenceIds.contains(ev.id);

                                  return CheckboxListTile(
                                    dense: true,
                                    value: isSelected,
                                    title: Text(ev.claimSupported, style: const TextStyle(color: Colors.white, fontSize: 11)),
                                    subtitle: Text('${ev.ladderLevel.code} • ${ev.source}', style: TextStyle(color: ev.ladderLevel.color, fontSize: 10)),
                                    onChanged: (checked) {
                                      setState(() {
                                        if (checked == true) {
                                          selectedEvidenceIds.add(ev.id);
                                        } else {
                                          selectedEvidenceIds.remove(ev.id);
                                        }
                                      });
                                    },
                                  );
                                },
                              ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: Text(L10nKey.commonCancel.tr, style: const TextStyle(color: Colors.white60)),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: selectedCategory.color,
                  foregroundColor: Colors.black,
                ),
                onPressed: () {
                  if (statementCtrl.text.trim().isNotEmpty) {
                    if (isStrengthOrWeakness && selectedEvidenceIds.isEmpty && evidences.isNotEmpty) {
                      // Tự động gán bằng chứng đầu tiên nếu chưa chọn để người dùng test nhanh
                      selectedEvidenceIds.add(evidences.first.id);
                    }
                    onCreateSwotItem(
                      selectedCategory,
                      statementCtrl.text.trim(),
                      importance,
                      selectedEvidenceIds,
                    );
                    Navigator.of(ctx).pop();
                  }
                },
                child: Text(L10nKey.swotSave.tr, style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF10B981).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              const Icon(Icons.verified_outlined, color: Color(0xFF10B981), size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  L10nKey.swotHeader.tr,
                  style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 2x2 SWOT Grid
        Expanded(
          child: GridView.count(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.25,
            children: SwotType.values.map((type) {
              final items = swotItems.where((s) => s.category == type).toList();

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: type.color.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title & Add
                    Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(color: type.color, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          type.localizedLabel,
                          style: TextStyle(color: type.color, fontSize: 13, fontWeight: FontWeight.bold),
                        ),
                        const Spacer(),
                        IconButton(
                          tooltip: L10nKey.swotAddTooltip.trParams({'type': type.localizedLabel}),
                          icon: Icon(Icons.add_circle_outline, color: type.color, size: 18),
                          onPressed: () => _showAddSwotDialog(context, type),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 10),

                    // Items list
                    Expanded(
                      child: items.isEmpty
                          ? Center(
                              child: Text(
                                L10nKey.swotEmpty.tr,
                                style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 11),
                              ),
                            )
                          : ListView.separated(
                              itemCount: items.length,
                              separatorBuilder: (_, _) => const SizedBox(height: 6),
                              itemBuilder: (context, idx) {
                                final item = items[idx];

                                return Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: 0.25),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        item.statement,
                                        style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w500),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 4),
                                      Row(
                                        children: [
                                          if (item.evidenceRefs.isNotEmpty)
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFF10B981).withValues(alpha: 0.15),
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  const Icon(Icons.link, color: Color(0xFF10B981), size: 10),
                                                  const SizedBox(width: 3),
                                                  Text(
                                                    '${item.evidenceRefs.length} Bằng Chứng',
                                                    style: const TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold),
                                                  ),
                                                ],
                                              ),
                                            )
                                          else
                                            Text(
                                              'Tín hiệu PESTEL',
                                              style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 9),
                                            ),
                                          const Spacer(),
                                          Text(
                                            'Trọng số: ${(item.importance * 100).toInt()}%',
                                            style: const TextStyle(color: Colors.white60, fontSize: 9),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
