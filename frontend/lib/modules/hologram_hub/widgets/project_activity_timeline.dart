import 'package:flutter/material.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_activity_inspector.dart';

class ProjectActivityTimeline extends StatefulWidget {
  final List<ProjectActivityEvent> events;
  final Function(ProjectActivityEvent event) onSelectEvent;
  final List<String>? filters;
  final bool loading;
  final bool unavailable;

  const ProjectActivityTimeline({
    super.key,
    required this.events,
    required this.onSelectEvent,
    this.filters,
    required this.loading,
    required this.unavailable,
  });

  @override
  State<ProjectActivityTimeline> createState() => _ProjectActivityTimelineState();
}

class _ProjectActivityTimelineState extends State<ProjectActivityTimeline> {
  ProjectActivityEvent? _selectedEvent;

  @override
  Widget build(BuildContext context) {
    if (widget.loading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF6366F1)),
      );
    }

    if (widget.unavailable) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.cloud_off,
              color: Colors.red,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Activity feed currently unavailable',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
    }

    // Filter events by kind if filters provided
    var filteredEvents = widget.events;
    if (widget.filters != null && widget.filters!.isNotEmpty) {
      filteredEvents = widget.events
          .where((e) => widget.filters!.any((f) => e.kind.startsWith(f)))
          .toList();
    }

    if (filteredEvents.isEmpty) {
      return Center(
        child: Text(
          'No activity recorded yet',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.5),
            fontSize: 14,
          ),
        ),
      );
    }

    // Sort by occurred time (newest first), handling nulls
    filteredEvents.sort((a, b) {
      if (a.occurredAt == null && b.occurredAt == null) return 0;
      if (a.occurredAt == null) return 1; // null goes to end
      if (b.occurredAt == null) return -1;
      return b.occurredAt!.compareTo(a.occurredAt!);
    });

    // Group by category
    final grouped = <String, List<ProjectActivityEvent>>{};
    for (final event in filteredEvents) {
      grouped.putIfAbsent(event.category, () => []).add(event);
    }

    return _selectedEvent != null
        ? ProjectActivityInspector(
            eventId: _selectedEvent!.eventId,
            projectId: _selectedEvent!.projectId,
            event: _selectedEvent,
            onClose: () => setState(() => _selectedEvent = null),
          )
        : ListView(
            children: grouped.entries.map((entry) {
              final category = entry.key;
              final categoryEvents = entry.value;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                    child: Text(
                      category,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  ...categoryEvents.map((event) {
                    return GestureDetector(
                      onTap: () {
                        setState(() => _selectedEvent = event);
                        widget.onSelectEvent(event);
                      },
                      child: Container(
                        margin: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 8,
                        ),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          border: Border.all(
                            color: const Color(0xFF334155),
                            width: 1,
                          ),
                          borderRadius: BorderRadius.circular(8),
                          color: const Color(0xFF1E293B).withValues(alpha: 0.5),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              _getIcon(event.category),
                              color: _getCategoryColor(event.category),
                              size: 20,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    event.displaySummary,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 13,
                                    ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 4),
                                  Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        '${event.actorKind ?? '?'}: ${event.actorId ?? '?'}',
                                        style: TextStyle(
                                          color: Colors.white.withValues(
                                            alpha: 0.5,
                                          ),
                                          fontSize: 11,
                                        ),
                                      ),
                                      Text(
                                        event.occurredAt != null
                                            ? _formatTime(event.occurredAt!)
                                            : '?',
                                        style: TextStyle(
                                          color: Colors.white.withValues(
                                            alpha: 0.5,
                                          ),
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              );
            }).toList(),
          );
  }

  IconData _getIcon(String category) {
    switch (category) {
      case 'Chat':
        return Icons.chat_bubble_outline;
      case 'Run':
        return Icons.play_circle_outline;
      case 'Tool':
        return Icons.settings_outlined;
      case 'Approval':
        return Icons.check_circle_outline;
      case 'Decision':
        return Icons.lightbulb_outline;
      case 'Task':
        return Icons.assignment_outlined;
      case 'Risk':
        return Icons.warning_amber_outlined;
      default:
        return Icons.info_outlined;
    }
  }

  Color _getCategoryColor(String category) {
    switch (category) {
      case 'Chat':
        return Colors.blue;
      case 'Run':
        return Colors.green;
      case 'Tool':
        return Colors.orange;
      case 'Approval':
        return Colors.yellow;
      case 'Decision':
        return Colors.purple;
      case 'Task':
        return Colors.cyan;
      case 'Risk':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final diff = now.difference(dateTime);

    if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else if (diff.inDays < 7) {
      return '${diff.inDays}d ago';
    } else {
      return '${dateTime.month}/${dateTime.day}';
    }
  }
}
