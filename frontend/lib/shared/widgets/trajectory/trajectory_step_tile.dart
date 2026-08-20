import 'package:flutter/material.dart';

class TrajectoryStepTile extends StatelessWidget {
  final Map<String, dynamic> step;
  final VoidCallback? onTap;

  const TrajectoryStepTile({super.key, required this.step, this.onTap});

  @override
  Widget build(BuildContext context) {
    final stepType = step['step_type'] ?? '';
    final title = step['title'] ?? 'Bước thực thi';
    final timestamp = step['timestamp'] ?? '';
    final badge = step['badge'];
    final durationMs = step['duration_ms'];

    IconData iconData = Icons.circle;
    Color iconColor = const Color(0xFF00F0FF);

    if (stepType == 'request_received') {
      iconData = Icons.person_outline;
      iconColor = Colors.white70;
    } else if (stepType == 'intent_classified') {
      iconData = Icons.psychology_outlined;
      iconColor = const Color(0xFF8A2BE2);
    } else if (stepType == 'tool_executed') {
      iconData = Icons.build_outlined;
      iconColor = const Color(0xFF00FF66);
    } else if (stepType == 'approval_pending') {
      iconData = Icons.security_outlined;
      iconColor = const Color(0xFFFF3366);
    } else if (stepType == 'artifact_created') {
      iconData = Icons.description_outlined;
      iconColor = const Color(0xFF00F0FF);
    }

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        margin: const EdgeInsets.symmetric(vertical: 3),
        decoration: BoxDecoration(
          color: const Color(0x10FFFFFF),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(iconData, color: iconColor, size: 16),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (timestamp.isNotEmpty)
                    Text(
                      timestamp.length > 19 ? timestamp.substring(11, 19) : timestamp,
                      style: const TextStyle(color: Colors.white38, fontSize: 10),
                    ),
                ],
              ),
            ),
            if (durationMs != null)
              Text("${durationMs}ms", style: const TextStyle(color: Colors.white38, fontSize: 10)),
            if (badge != null) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: badge == 'HIGH' || badge == 'HIGH_RISK' ? const Color(0x30FF3366) : const Color(0x3000FF66),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(badge, style: const TextStyle(color: Colors.white, fontSize: 9)),
              )
            ]
          ],
        ),
      ),
    );
  }
}
