import 'package:flutter/material.dart';

class ReconciliationCard extends StatelessWidget {
  final String transactionId;
  final String amount;
  final String direction;
  final String description;
  final String? counterparty;
  final String documentNumber;
  final String documentType;
  final double confidence;
  final VoidCallback onAccept;

  const ReconciliationCard({
    super.key,
    required this.transactionId,
    required this.amount,
    required this.direction,
    required this.description,
    this.counterparty,
    required this.documentNumber,
    required this.documentType,
    required this.confidence,
    required this.onAccept,
  });

  @override
  Widget build(BuildContext context) {
    final isIncome = direction.toUpperCase() == 'IN';
    final confPercent = (confidence * 100).toStringAsFixed(0);

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
                Row(
                  children: [
                    Icon(
                      isIncome ? Icons.arrow_downward : Icons.arrow_upward,
                      color: isIncome ? Colors.green : Colors.red,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '$amount VND',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.blue.withValues(alpha: 0.1),

                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Khớp: $confPercent%',
                    style: const TextStyle(
                      color: Colors.blue,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              description,
              style: TextStyle(color: Colors.grey[800], fontSize: 14),
            ),
            if (counterparty != null) ...[
              const SizedBox(height: 4),
              Text(
                'Đối tác: $counterparty',
                style: TextStyle(color: Colors.grey[600], fontSize: 13),
              ),
            ],
            const Divider(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Chứng từ TT58 gợi ý:',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                    Text(
                      '$documentType #$documentNumber',
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: onAccept,
                  icon: const Icon(Icons.check, size: 16),
                  label: const Text('Chấp nhận'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.indigo,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
