import 'package:flutter/material.dart';

class CitationCard extends StatelessWidget {
  final String sourceRegulationNumber;
  final String sourceRegulationVersion;
  final String? layer; // CURRENT_LAW | POLICY_WATCH | PROFESSIONAL_REVIEW
  final String? url;
  final double? confidence;
  final List<String> assumptions;

  const CitationCard({
    super.key,
    required this.sourceRegulationNumber,
    required this.sourceRegulationVersion,
    this.layer,
    this.url,
    this.confidence,
    this.assumptions = const [],
  });

  Color _getLayerColor(BuildContext context) {
    switch (layer) {
      case 'CURRENT_LAW':
        return Colors.green;
      case 'POLICY_WATCH':
        return Colors.amber;
      case 'PROFESSIONAL_REVIEW':
        return Colors.purple;
      default:
        return Colors.blueGrey;
    }
  }

  String _getLayerLabel() {
    switch (layer) {
      case 'CURRENT_LAW':
        return 'LUẬT HIỆN HÀNH';
      case 'POLICY_WATCH':
        return 'THEO DÕI CHÍNH SÁCH';
      case 'PROFESSIONAL_REVIEW':
        return 'CẦN CHUYÊN GIA';
      default:
        return 'NGUỒN THAM KHẢO';
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _getLayerColor(context);

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6.0),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: color.withOpacity(0.4), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _getLayerLabel(),
                    style: TextStyle(
                      color: color,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const Spacer(),
                if (confidence != null)
                  Text(
                    'Độ tin cậy: ${(confidence! * 100).toStringAsFixed(0)}%',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '$sourceRegulationNumber (Phiên bản: $sourceRegulationVersion)',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            if (url != null && url!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                url!,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.primary,
                  fontSize: 12,
                  decoration: TextDecoration.underline,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            if (assumptions.isNotEmpty) ...[
              const SizedBox(height: 8),
              const Divider(),
              Text(
                'Giả định áp dụng:',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              ...assumptions.map(
                (a) => Padding(
                  padding: const EdgeInsets.only(top: 2.0, left: 4.0),
                  child: Text(
                    '• $a',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
