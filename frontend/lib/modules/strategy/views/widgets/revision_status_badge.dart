import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

/// Badge trạng thái revision dùng chung cho Canvas Overview/Foundation tab -
/// đúng nguyên tắc UI §5.1 "Luôn hiện revision badge: Draft, In review, Approved,
/// Stale hoặc Superseded".
class RevisionStatusBadge extends StatelessWidget {
  final String status;
  const RevisionStatusBadge({super.key, required this.status});

  static const _labels = {
    'draft': 'Nháp',
    'in_review': 'Đang duyệt',
    'approved': 'Đã duyệt',
    'changes_requested': 'Yêu cầu sửa',
    'superseded': 'Đã thay thế',
    'archived': 'Lưu trữ',
  };

  Color _color() {
    switch (status) {
      case 'approved':
        return AppTheme.secondary;
      case 'in_review':
        return Colors.amberAccent;
      case 'changes_requested':
        return AppTheme.accent;
      case 'superseded':
      case 'archived':
        return AppTheme.textMutedDark;
      default:
        return AppTheme.primaryLight;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(
        _labels[status] ?? status,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}
