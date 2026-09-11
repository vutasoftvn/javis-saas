import 'package:flutter/material.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';

class ProjectActivityInspector extends StatelessWidget {
  final String eventId;
  final String projectId;
  final ProjectActivityEvent? event;
  final VoidCallback? onClose;

  const ProjectActivityInspector({
    super.key,
    required this.eventId,
    required this.projectId,
    this.event,
    this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    if (event == null) {
      return Center(
        child: Text(
          'Event not found',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.7),
          ),
        ),
      );
    }

    return SingleChildScrollView(
      child: Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with close button
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Activity Details',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (onClose != null)
                  IconButton(
                    onPressed: onClose,
                    icon: const Icon(Icons.close, color: Colors.white70),
                  ),
              ],
            ),
            const Divider(color: Color(0x226366F1)),
            const SizedBox(height: 16),

            // Event ID
            _buildField(
              label: 'Event ID',
              value: event!.eventId,
            ),

            // Correlation ID
            if (event!.correlationId != null)
              _buildField(
                label: 'Correlation ID',
                value: event!.correlationId!,
              ),

            // Source Reference
            if (event!.sourceType != null)
              _buildField(
                label: 'Source Type',
                value: event!.sourceType!.toUpperCase(),
              ),
            if (event!.sourceId != null)
              _buildField(
                label: 'Source ID',
                value: event!.sourceId!,
              ),

            // Status
            if (event!.status != null)
              _buildField(
                label: 'Status',
                value: event!.status!.toUpperCase(),
              ),

            // Kind
            _buildField(
              label: 'Kind',
              value: event!.kind,
            ),

            // Phase
            if (event!.phase != null)
              _buildField(
                label: 'Phase',
                value: event!.phase!,
              ),

            // Actor
            if (event!.actorKind != null || event!.actorId != null)
              _buildField(
                label: 'Actor',
                value: '${event!.actorKind ?? '?'}: ${event!.actorId ?? '?'}',
              ),

            // Safety Level
            if (event!.classification != null && event!.classification!.isNotEmpty)
              _buildField(
                label: 'Classification',
                value: event!.classification!,
              ),

            // Summary (safe content)
            const SizedBox(height: 16),
            const Text(
              'Summary (Redacted)',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Text(
                event!.displaySummary,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
            ),

            const SizedBox(height: 16),
            if (event!.classification == 'restricted')
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.orange, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Restricted: nội dung đã được ẩn để bảo mật.',
                        style: TextStyle(
                          color: Colors.orange,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 24),
            const Text(
              'Note: Raw prompts, tokens, secrets, and sensitive payloads are not displayed for security.',
              style: TextStyle(
                color: Colors.white54,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildField({required String label, required String value}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 11,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B).withValues(alpha: 0.8),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: const Color(0xFF334155),
                width: 1,
              ),
            ),
            child: Text(
              value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontFamily: 'monospace',
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
