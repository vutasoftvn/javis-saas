import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../shared/widgets/evidence_ladder_badge.dart';

class EvidenceItemCard extends StatelessWidget {
  final EvidenceModel evidence;
  final VoidCallback? onDelete;

  const EvidenceItemCard({
    super.key,
    required this.evidence,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isSupports = evidence.direction == 'supports';
    final dirColor = isSupports ? const Color(0xFF10B981) : const Color(0xFFEF4444);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: dirColor.withValues(alpha: 0.25),
          width: 1.0,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              EvidenceLadderBadge(level: evidence.ladderLevel, isCompact: true),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: dirColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  isSupports ? 'Ủng Hộ (+)' : 'Phủ Định (-)',
                  style: TextStyle(
                    color: dirColor,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                'Độ mạnh: ${evidence.strength.toUpperCase()}',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.45),
                  fontSize: 10,
                ),
              ),
              if (onDelete != null) ...[
                const SizedBox(width: 4),
                InkWell(
                  onTap: onDelete,
                  child: Icon(Icons.close, size: 14, color: Colors.white.withValues(alpha: 0.4)),
                ),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Text(
            evidence.claimSupported,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w500,
              height: 1.3,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Icon(Icons.link, size: 12, color: Colors.white.withValues(alpha: 0.4)),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  evidence.source,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.55),
                    fontSize: 11,
                    fontStyle: FontStyle.italic,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
