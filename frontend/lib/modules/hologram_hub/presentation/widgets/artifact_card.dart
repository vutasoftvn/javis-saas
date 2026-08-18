import 'package:flutter/material.dart';

class ArtifactCard extends StatelessWidget {
  final String title;
  final String type;
  final String status;
  final String? createdAt;
  final VoidCallback? onTap;

  const ArtifactCard({
    super.key,
    required this.title,
    required this.type,
    required this.status,
    this.createdAt,
    this.onTap,
  });

  IconData _getTypeIcon() {
    switch (type.toLowerCase()) {
      case 'document':
        return Icons.description_outlined;
      case 'code':
        return Icons.code_rounded;
      case 'spreadsheet':
        return Icons.table_chart_outlined;
      case 'research_bundle':
        return Icons.auto_stories_outlined;
      case 'media':
        return Icons.image_outlined;
      default:
        return Icons.folder_open_outlined;
    }
  }

  Color _getStatusColor() {
    switch (status.toLowerCase()) {
      case 'published':
      case 'approved':
      case 'completed':
      case 'succeeded':
        return const Color(0xFF10B981); // Emerald
      case 'waiting_approval':
      case 'review':
        return const Color(0xFFF59E0B); // Amber
      case 'running':
        return const Color(0xFF14B8A6); // Cyan
      case 'failed':
        return const Color(0xFFEF4444); // Red
      case 'draft':
      default:
        return const Color(0xFF818CF8); // Indigo
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _getStatusColor();

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white.withValues(alpha: 0.08),
                Colors.white.withValues(alpha: 0.02),
              ],
            ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.35),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                ),
                child: Icon(_getTypeIcon(), size: 18, color: statusColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Text(
                          type.toUpperCase(),
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF64748B),
                            letterSpacing: 0.5,
                          ),
                        ),
                        if (createdAt != null && createdAt!.isNotEmpty) ...[
                          const SizedBox(width: 6),
                          const Text('•', style: TextStyle(color: Color(0xFF475569), fontSize: 14)),
                          const SizedBox(width: 6),
                          Text(
                            createdAt!,
                            style: const TextStyle(fontSize: 14, color: Color(0xFF64748B)),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                ),
                child: Text(
                  status.toUpperCase(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
