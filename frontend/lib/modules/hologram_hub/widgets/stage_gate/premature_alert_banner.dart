import 'package:flutter/material.dart';
import '../../../../data/models/stage_gate_model.dart';

class PrematureAlertBanner extends StatelessWidget {
  final List<PrematureAlertModel> alerts;
  final Function(int alertId)? onDismiss;

  const PrematureAlertBanner({
    super.key,
    required this.alerts,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final activeAlerts = alerts.where((a) => !a.isDismissed).toList();
    if (activeAlerts.isEmpty) return const SizedBox.shrink();

    final firstAlert = activeAlerts.first;
    final color = firstAlert.severity.color;

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.45), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.15),
            blurRadius: 12,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(firstAlert.severity.icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      firstAlert.title,
                      style: TextStyle(
                        color: color,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        firstAlert.severity.name.toUpperCase(),
                        style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  firstAlert.message,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.8),
                    fontSize: 11,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
          if (activeAlerts.length > 1)
            Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '+${activeAlerts.length - 1} cảnh báo khác',
                style: const TextStyle(color: Colors.white70, fontSize: 10),
              ),
            ),
          if (onDismiss != null)
            IconButton(
              icon: const Icon(Icons.close, color: Colors.white60, size: 16),
              onPressed: () => onDismiss!(firstAlert.id),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            ),
        ],
      ),
    );
  }
}
