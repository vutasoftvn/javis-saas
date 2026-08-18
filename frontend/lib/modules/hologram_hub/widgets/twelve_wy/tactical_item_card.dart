import 'package:flutter/material.dart';
import '../../../../data/models/twelve_wy_model.dart';

class TacticalItemCard extends StatelessWidget {
  final TacticalItemModel tactic;
  final ValueChanged<int>? onCountChanged;
  final ValueChanged<bool>? onToggleDone;

  const TacticalItemCard({
    super.key,
    required this.tactic,
    this.onCountChanged,
    this.onToggleDone,
  });

  @override
  Widget build(BuildContext context) {
    final isDone = tactic.isDone;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDone
              ? const Color(0xFF10B981).withValues(alpha: 0.4)
              : Colors.white.withValues(alpha: 0.1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Checkbox + Title + Owner
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              InkWell(
                onTap: onToggleDone != null ? () => onToggleDone!(!isDone) : null,
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  width: 20,
                  height: 20,
                  margin: const EdgeInsets.only(top: 2, right: 10),
                  decoration: BoxDecoration(
                    color: isDone ? const Color(0xFF10B981) : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: isDone ? const Color(0xFF10B981) : Colors.white38,
                      width: 1.5,
                    ),
                  ),
                  child: isDone
                      ? const Icon(Icons.check, size: 14, color: Colors.white)
                      : null,
                ),
              ),

              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tactic.title,
                      style: TextStyle(
                        color: isDone ? Colors.white60 : Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        decoration: isDone ? TextDecoration.lineThrough : null,
                      ),
                    ),
                    if (tactic.description.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        tactic.description,
                        style: const TextStyle(color: Colors.white54, fontSize: 11),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),

              // Owner Role Pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  tactic.ownerRole,
                  style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),

          const SizedBox(height: 10),

          // Lead Indicator Controller Row
          Row(
            children: [
              // Lead Indicator Label
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFA855F7).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFA855F7).withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.trending_up, size: 12, color: Color(0xFFA855F7)),
                    const SizedBox(width: 4),
                    Text(
                      tactic.leadIndicatorName,
                      style: const TextStyle(color: Color(0xFFC084FC), fontSize: 11, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),

              const Spacer(),

              // Decrement Button
              InkWell(
                onTap: onCountChanged != null && tactic.actualCount > 0
                    ? () => onCountChanged!(tactic.actualCount - 1)
                    : null,
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Icon(Icons.remove, size: 12, color: Colors.white70),
                ),
              ),
              const SizedBox(width: 8),

              // Count Display
              Text(
                '${tactic.actualCount} / ${tactic.targetCount}',
                style: TextStyle(
                  color: isDone ? const Color(0xFF10B981) : Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 8),

              // Increment Button
              InkWell(
                onTap: onCountChanged != null
                    ? () => onCountChanged!(tactic.actualCount + 1)
                    : null,
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Icon(Icons.add, size: 12, color: Color(0xFF10B981)),
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Progress Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: tactic.progressRatio,
              backgroundColor: Colors.white10,
              valueColor: AlwaysStoppedAnimation<Color>(
                isDone ? const Color(0xFF10B981) : const Color(0xFF38BDF8),
              ),
              minHeight: 4,
            ),
          ),
        ],
      ),
    );
  }
}
