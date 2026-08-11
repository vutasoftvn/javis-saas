import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

/// Bảng Evidence với cột Source/Fact/Date/Reliability/Selected (§5.3: "Evidence
/// table có Source, Fact, Date, Reliability, Link và Selected. Chỉ evidence
/// selected đi vào Context Pack gửi AI").
class EvidenceTable extends StatelessWidget {
  final List<dynamic> evidence;
  final Set<String> selectedIds;
  final ValueChanged<String> onToggle;

  const EvidenceTable({
    super.key,
    required this.evidence,
    required this.selectedIds,
    required this.onToggle,
  });

  Color _reliabilityColor(String? reliability) {
    switch (reliability) {
      case 'high':
        return AppTheme.secondary;
      case 'medium':
        return Colors.amberAccent;
      case 'low':
        return AppTheme.accent;
      default:
        return AppTheme.textMutedDark;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (evidence.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Text('Chưa có evidence nào trong workspace.', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Chọn')),
          DataColumn(label: Text('Nguồn')),
          DataColumn(label: Text('Nội dung')),
          DataColumn(label: Text('Loại')),
          DataColumn(label: Text('Độ tin cậy')),
        ],
        rows: evidence.map<DataRow>((item) {
          final id = item['id'] as String;
          final selected = selectedIds.contains(id);
          return DataRow(
            selected: selected,
            onSelectChanged: (_) => onToggle(id),
            cells: [
              DataCell(Checkbox(value: selected, onChanged: (_) => onToggle(id))),
              DataCell(SizedBox(width: 160, child: Text(item['title'] ?? '', overflow: TextOverflow.ellipsis))),
              DataCell(SizedBox(width: 260, child: Text(item['summary'] ?? '', overflow: TextOverflow.ellipsis, maxLines: 2))),
              DataCell(Text(item['source_type'] ?? '')),
              DataCell(Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: _reliabilityColor(item['reliability']).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(item['reliability'] ?? '', style: TextStyle(color: _reliabilityColor(item['reliability']))),
              )),
            ],
          );
        }).toList(),
      ),
    );
  }
}
