import 'package:flutter/material.dart';
import '../../../core/capabilities/capability_gate.dart';
import '../../../shared/widgets/ai_advisory_disclosure.dart';
import '../models/chat_models.dart';


class SessionStatusBadge extends StatelessWidget {
  final String status;

  const SessionStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    IconData icon;
    String label = status.toUpperCase();

    switch (status.toLowerCase()) {
      case 'running':
        bg = Colors.blue.shade50;
        fg = Colors.blue.shade700;
        icon = Icons.sync;
        break;
      case 'waiting_approval':
        bg = Colors.orange.shade50;
        fg = Colors.orange.shade800;
        icon = Icons.hourglass_top;
        label = 'WAITING APPROVAL';
        break;
      case 'completed':
        bg = Colors.green.shade50;
        fg = Colors.green.shade700;
        icon = Icons.check_circle;
        break;
      case 'failed':
        bg = Colors.red.shade50;
        fg = Colors.red.shade700;
        icon = Icons.error;
        break;
      case 'idle':
      default:
        bg = Colors.grey.shade100;
        fg = Colors.grey.shade700;
        icon = Icons.pause_circle_outline;
        label = 'IDLE';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: fg.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: fg),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: fg,
            ),
          ),
        ],
      ),
    );
  }
}

class SessionArtifactsDrawer extends StatelessWidget {
  final List<WorkspaceArtifactModel> artifacts;
  final Function(WorkspaceArtifactModel)? onSelectArtifact;

  const SessionArtifactsDrawer({
    super.key,
    required this.artifacts,
    this.onSelectArtifact,
  });

  @override
  Widget build(BuildContext context) {
    if (artifacts.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Text(
            'No artifacts produced yet for this session.',
            style: TextStyle(color: Colors.grey),
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: artifacts.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final art = artifacts[index];
        IconData icon = Icons.insert_drive_file;
        if (art.artifactKind == 'report') icon = Icons.description;
        if (art.artifactKind == 'table') icon = Icons.table_chart;
        if (art.artifactKind == 'file_export') icon = Icons.download;

        return ListTile(
          leading: CircleAvatar(
            backgroundColor: Colors.indigo.shade50,
            child: Icon(icon, color: Colors.indigo, size: 20),
          ),
          title: Text(
            art.displayName,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
          ),
          subtitle: Text(
            '${art.artifactKind} • ${art.mediaType}',
            style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
          ),
          trailing: const Icon(Icons.chevron_right, size: 18),
          onTap: () => onSelectArtifact?.call(art),
        );
      },
    );
  }
}

class SessionHeaderBar extends StatelessWidget {
  final SessionViewModel sessionView;
  final VoidCallback onOpenArtifacts;
  final VoidCallback onManageSchedules;

  const SessionHeaderBar({
    super.key,
    required this.sessionView,
    required this.onOpenArtifacts,
    required this.onManageSchedules,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Text(
                      sessionView.title,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(width: 8),
                    SessionStatusBadge(status: sessionView.status),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Text(
                      'Profile: ${sessionView.agentProfile ?? 'operations'}',
                      style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                    ),
                    if (sessionView.enabledConnectorKeys.isNotEmpty) ...[
                      const SizedBox(width: 8),
                      const Text('•', style: TextStyle(color: Colors.grey)),
                      const SizedBox(width: 8),
                      ...sessionView.enabledConnectorKeys.map(
                        (k) => Padding(
                          padding: const EdgeInsets.only(right: 4.0),
                          child: Chip(
                            label: Text(k, style: const TextStyle(fontSize: 10)),
                            padding: EdgeInsets.zero,
                            materialTapTargetSize:
                                MaterialTapTargetSize.shrinkWrap,
                            backgroundColor: CapabilityGate.canUseConnector(k)
                                ? Colors.teal.shade50
                                : Colors.red.shade50,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 6),
                const AiAdvisoryDisclosure(domain: 'Phiên làm việc AI', hasDataWarning: false),
              ],
            ),
          ),

          IconButton(
            icon: const Icon(Icons.alarm, size: 20),
            tooltip: 'Schedules',
            onPressed: onManageSchedules,
          ),
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.folder_outlined, size: 20),
                tooltip: 'Artifacts',
                onPressed: onOpenArtifacts,
              ),
              if (sessionView.artifacts.isNotEmpty)
                Positioned(
                  right: 6,
                  top: 6,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: Colors.indigo,
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      '${sessionView.artifacts.length}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
