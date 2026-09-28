import 'package:flutter/material.dart';
import '../../models/ai_initiative_portfolio.dart';

class AiInitiativePortfolioCard extends StatelessWidget {
  final AiInitiativePortfolioItem item;
  final VoidCallback? onScale;
  final VoidCallback? onPromote;

  const AiInitiativePortfolioCard({
    super.key,
    required this.item,
    this.onScale,
    this.onPromote,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasBaseline = item.baselineMetricValue != null && item.baselineMetricValue!.trim().isNotEmpty;
    final canScale = item.authorizedActions.contains('scale_initiative');

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Title & Lifecycle State
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    item.title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Chip(
                  label: Text(
                    item.lifecycleState,
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                  backgroundColor: _getLifecycleColor(item.lifecycleState).withOpacity(0.2),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Governance Badges: Risk & Autonomy
            Row(
              children: [
                _buildBadge('Risk: ${item.riskTier}', Colors.orange),
                const SizedBox(width: 8),
                _buildBadge('Autonomy: ${item.autonomyTier}', Colors.blue),
                const SizedBox(width: 8),
                _buildBadge('Budget: ${item.costBudgetStatus}', _getBudgetColor(item.costBudgetStatus)),
              ],
            ),
            const Divider(height: 24),

            // Value & Metric row
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Baseline', style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text(
                        hasBaseline ? item.baselineMetricValue! : 'Chưa có baseline',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: hasBaseline ? Colors.black87 : Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Target', style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text(
                        item.targetMetricValue ?? 'Chưa xác định',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Latest Outcome', style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text(
                        item.latestOutcomeValue ?? 'Chưa đo',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Next gate
            Row(
              children: [
                const Icon(Icons.flag_outlined, size: 16, color: Colors.blueGrey),
                const SizedBox(width: 6),
                Text(
                  'Next Gate: ${item.nextRequiredGate}',
                  style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w500),
                ),
              ],
            ),

            // Blocking reasons if any
            if (item.blockingReasons.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, size: 16, color: Colors.red),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        item.blockingReasons.join(', '),
                        style: TextStyle(fontSize: 12, color: Colors.red.shade900),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Action CTAs
            if (canScale) ...[
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton.icon(
                  key: const Key('scale_initiative'),
                  onPressed: onScale,
                  icon: const Icon(Icons.rocket_launch, size: 16),
                  label: const Text('Scale Sáng kiến'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green.shade700,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: color),
      ),
    );
  }

  Color _getLifecycleColor(String state) {
    switch (state) {
      case 'SCALED':
        return Colors.green;
      case 'SCALE_CANDIDATE':
        return Colors.teal;
      case 'VALIDATE':
        return Colors.blue;
      case 'PILOT':
        return Colors.purple;
      case 'PAUSED':
        return Colors.amber;
      case 'RETIRED':
        return Colors.grey;
      default:
        return Colors.blueGrey;
    }
  }

  Color _getBudgetColor(String status) {
    switch (status) {
      case 'OK':
        return Colors.green;
      case 'EXCEEDED':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }
}
