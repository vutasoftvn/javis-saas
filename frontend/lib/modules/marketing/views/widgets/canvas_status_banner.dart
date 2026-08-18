import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'epistemic_badge.dart';

class CanvasStatusBanner extends StatelessWidget {
  final String canvasKey;
  final String canvasTitle;
  final Map<String, dynamic> statusData;
  final VoidCallback? onExtractAssumptions;

  const CanvasStatusBanner({
    super.key,
    required this.canvasKey,
    required this.canvasTitle,
    required this.statusData,
    this.onExtractAssumptions,
  });

  @override
  Widget build(BuildContext context) {
    final status = (statusData['status'] as String?) ?? 'draft';
    final total = statusData['total_assumptions'] ?? 0;
    final untested = statusData['untested_count'] ?? 0;
    final supported = statusData['supported_count'] ?? 0;
    final contradicted = statusData['contradicted_count'] ?? 0;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: contradicted > 0
              ? AppTheme.error.withValues(alpha: 0.4)
              : AppTheme.borderDark.withValues(alpha: 0.6),
        ),
      ),
      child: Row(
        children: [
          EpistemicBadge(status: status),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              '$canvasTitle: $total giả định ($supported đã xác thực, $untested chưa đo, $contradicted bị bác bỏ)',
              style: TextStyle(
                fontSize: 12,
                color: contradicted > 0 ? AppTheme.error : AppTheme.textMutedDark,
                fontWeight: contradicted > 0 ? FontWeight.w600 : FontWeight.normal,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (onExtractAssumptions != null) ...[
            const SizedBox(width: 8),
            InkWell(
              onTap: onExtractAssumptions,
              borderRadius: BorderRadius.circular(6),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppTheme.primaryLight.withValues(alpha: 0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.auto_awesome_rounded, size: 13, color: AppTheme.primaryLight),
                    const SizedBox(width: 4),
                    Text(
                      'AI Trích xuất giả định',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.primaryLight),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
