import 'package:flutter/material.dart';

class TokenSavingsBadge extends StatelessWidget {
  final int rtkTokensSaved;
  final int cavemanTokensSaved;
  final double estimatedCostSavedUsd;

  const TokenSavingsBadge({
    super.key,
    this.rtkTokensSaved = 142800,
    this.cavemanTokensSaved = 86400,
    this.estimatedCostSavedUsd = 2.40,
  });

  String _formatNumber(int n) {
    if (n >= 1000000) {
      return '${(n / 1000000).toStringAsFixed(1)}M';
    }
    if (n >= 1000) {
      return '${(n / 1000).toStringAsFixed(1)}K';
    }
    return n.toString();
  }

  @override
  Widget build(BuildContext context) {
    final totalTokens = rtkTokensSaved + cavemanTokensSaved;

    return Tooltip(
      message: 'RTK Token Saver: -${_formatNumber(rtkTokensSaved)} input tokens\n'
          'Caveman Mode: -${_formatNumber(cavemanTokensSaved)} output tokens\n'
          'Chi phí tiết kiệm ước tính: ~\$${estimatedCostSavedUsd.toStringAsFixed(2)} USD',
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
      ),
      textStyle: const TextStyle(color: Colors.white, fontSize: 12, height: 1.4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: const Color(0xFF10B981).withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.35)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.energy_savings_leaf_rounded, color: Color(0xFF10B981), size: 14),
            const SizedBox(width: 6),
            Text(
              'SAVED ${_formatNumber(totalTokens)} TOKENS',
              style: const TextStyle(
                color: Color(0xFF10B981),
                fontSize: 11,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              '(~\$${estimatedCostSavedUsd.toStringAsFixed(2)})',
              style: TextStyle(
                color: const Color(0xFF10B981).withValues(alpha: 0.8),
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
