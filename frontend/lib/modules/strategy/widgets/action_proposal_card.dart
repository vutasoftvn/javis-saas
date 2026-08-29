import 'package:flutter/material.dart';

class ActionProposalCard extends StatelessWidget {
  final String proposalId;
  final String source;
  final String recommendation;
  final int priority;
  final String decisionReason;
  final String? capabilityRequired;
  final VoidCallback onAccept;

  const ActionProposalCard({
    super.key,
    required this.proposalId,
    required this.source,
    required this.recommendation,
    required this.priority,
    required this.decisionReason,
    this.capabilityRequired,
    required this.onAccept,
  });

  Color _getSourceColor() {
    switch (source.toLowerCase()) {
      case 'legal':
        return Colors.amber.shade800;
      case 'finance':
        return Colors.green.shade700;
      case 'stage':
        return Colors.indigo;
      case 'evidence':
        return Colors.purple;
      default:
        return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final srcColor = _getSourceColor();

    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: srcColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    source.toUpperCase(),
                    style: TextStyle(
                      color: srcColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.grey.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Ưu tiên: $priority',
                    style: const TextStyle(
                      color: Colors.grey,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              recommendation,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline, size: 16, color: Colors.blueGrey),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Căn cứ: $decisionReason',
                      style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
                    ),
                  ),
                ],
              ),
            ),
            if (capabilityRequired != null) ...[
              const SizedBox(height: 6),
              Text(
                'Capability yêu cầu: $capabilityRequired',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
              ),
            ],
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton.icon(
                onPressed: onAccept,
                icon: const Icon(Icons.check, size: 16),
                label: const Text('Chấp nhận hành động'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: srcColor,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
