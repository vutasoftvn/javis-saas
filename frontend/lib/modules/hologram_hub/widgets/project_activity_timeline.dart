import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_activity_inspector.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';

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

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode != 'vi';
  }

  @override
  Widget build(BuildContext context) {
    final isEn = _isEnglish();
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
            const Icon(
              Icons.cloud_off,
              color: Colors.red,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              isEn
                  ? 'Activity feed currently unavailable'
                  : 'Dòng hoạt động hiện chưa khả dụng',
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
          isEn ? 'No activity recorded yet' : 'Chưa có hoạt động nào được ghi nhận',
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
            padding: const EdgeInsets.symmetric(vertical: 4),
            children: grouped.entries.map((entry) {
              final category = entry.key;
              final categoryEvents = entry.value;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildCategoryHeader(category, categoryEvents.length, isEn),
                  ...categoryEvents.map((event) => _buildEventCard(event, isEn)),
                ],
              );
            }).toList(),
          );
  }

  Widget _buildCategoryHeader(String category, int count, bool isEn) {
    String label = category;
    if (category == 'Run') {
      label = isEn ? 'RUN EXECUTIONS' : 'TIẾN TRÌNH THỰC THI';
    } else if (category == 'Chat') {
      label = isEn ? 'CONVERSATIONS' : 'HỘI THOẠI';
    } else if (category == 'Tool') {
      label = isEn ? 'TOOL CALLS' : 'CÔNG CỤ';
    } else if (category == 'Approval') {
      label = isEn ? 'APPROVAL REQUESTS' : 'YÊU CẦU PHÊ DUYỆT';
    } else if (category == 'Decision') {
      label = isEn ? 'STRATEGIC DECISIONS' : 'QUYẾT ĐỊNH CHIẾN LƯỢC';
    } else if (category == 'Task') {
      label = isEn ? 'WORK TASKS' : 'NHIỆM VỤ';
    } else if (category == 'Risk') {
      label = isEn ? 'RISK ALERTS' : 'CẢNH BÁO RỦI RO';
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
      child: Row(
        children: [
          Icon(
            _getIcon(category),
            color: _getCategoryColor(category),
            size: 14,
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 11,
              letterSpacing: 0.5,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
            decoration: BoxDecoration(
              color: const Color(0xFF334155),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$count',
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEventCard(ProjectActivityEvent event, bool isEn) {
    final statusText = event.formatStatus(isEn: isEn);
    final statusColor = _getStatusColor(event.status ?? event.phase ?? event.kind);
    final categoryColor = _getCategoryColor(event.category);
    final stepName = event.stepName;
    final title = event.getFormattedTitle(isEn: isEn);

    return GestureDetector(
      onTap: () {
        setState(() => _selectedEvent = event);
        widget.onSelectEvent(event);
      },
      child: Container(
        margin: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 5,
        ),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(
            color: const Color(0xFF334155),
            width: 1,
          ),
          borderRadius: BorderRadius.circular(10),
          color: const Color(0xFF1E293B).withValues(alpha: 0.55),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: categoryColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: categoryColor.withValues(alpha: 0.3),
                  width: 1,
                ),
              ),
              child: Center(
                child: Icon(
                  _getEventIcon(event),
                  color: categoryColor,
                  size: 18,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header Row: Title & Status Badge
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            height: 1.3,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (statusText != null) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: statusColor.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: statusColor.withValues(alpha: 0.4),
                              width: 0.8,
                            ),
                          ),
                          child: Text(
                            statusText,
                            style: TextStyle(
                              color: statusColor,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),

                  // Step Name chip if present
                  if (stepName != null) ...[
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 1.5,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: const Color(0xFF334155),
                          width: 0.8,
                        ),
                      ),
                      child: Text(
                        isEn ? 'Step: $stepName' : 'Bước: $stepName',
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 10.5,
                        ),
                      ),
                    ),
                  ],

                  const SizedBox(height: 7),

                  // Footer Row: Actor & Timestamp
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _getActorIcon(event.actorKind),
                            size: 13,
                            color: Colors.white54,
                          ),
                          const SizedBox(width: 5),
                          Text(
                            event.formatActor(isEn: isEn),
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.65),
                              fontSize: 11,
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                        ],
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.access_time_rounded,
                            size: 12,
                            color: Colors.white.withValues(alpha: 0.4),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            event.occurredAt != null
                                ? _formatTime(event.occurredAt!)
                                : '?',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.55),
                              fontSize: 11,
                            ),
                          ),
                        ],
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
  }

  IconData _getIcon(String category) {
    switch (category) {
      case 'Chat':
        return Icons.chat_bubble_outline_rounded;
      case 'Run':
        return Icons.play_circle_outline_rounded;
      case 'Tool':
        return Icons.settings_outlined;
      case 'Approval':
        return Icons.check_circle_outline_rounded;
      case 'Decision':
        return Icons.lightbulb_outline_rounded;
      case 'Task':
        return Icons.assignment_outlined;
      case 'Risk':
        return Icons.warning_amber_rounded;
      default:
        return Icons.info_outline_rounded;
    }
  }

  IconData _getEventIcon(ProjectActivityEvent event) {
    final k = event.kind.toLowerCase();
    final s = (event.status ?? event.phase ?? '').toLowerCase();

    if (k.startsWith('run.')) {
      if (s == 'completed' || s == 'success' || k == 'run.completed') {
        return Icons.check_circle_rounded;
      }
      if (s == 'failed' || s == 'error' || k == 'run.failed') {
        return Icons.cancel_rounded;
      }
      if (k == 'run.waiting_approval' || s == 'waiting_approval') {
        return Icons.pause_circle_filled_rounded;
      }
      if (k == 'run.queued') {
        return Icons.schedule_rounded;
      }
      return Icons.play_circle_fill_rounded;
    }

    return _getIcon(event.category);
  }

  IconData _getActorIcon(String? actorKind) {
    final k = (actorKind ?? '').toLowerCase();
    if (k == 'principal' || k == 'human' || k == 'user') {
      return Icons.person_rounded;
    }
    if (k == 'agent' || k == 'ai') {
      return Icons.smart_toy_rounded;
    }
    if (k == 'system') {
      return Icons.settings_suggest_rounded;
    }
    return Icons.account_circle_outlined;
  }

  Color _getCategoryColor(String category) {
    switch (category) {
      case 'Chat':
        return const Color(0xFF38BDF8);
      case 'Run':
        return const Color(0xFF22C55E);
      case 'Tool':
        return const Color(0xFFFB923C);
      case 'Approval':
        return const Color(0xFFFBBF24);
      case 'Decision':
        return const Color(0xFFA855F7);
      case 'Task':
        return const Color(0xFF06B6D4);
      case 'Risk':
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF94A3B8);
    }
  }

  Color _getStatusColor(String statusOrKind) {
    final s = statusOrKind.toLowerCase();
    if (s.contains('completed') || s.contains('success') || s.contains('resolved')) {
      return const Color(0xFF22C55E);
    }
    if (s.contains('failed') || s.contains('error') || s.contains('denied')) {
      return const Color(0xFFEF4444);
    }
    if (s.contains('running') || s.contains('in_progress') || s.contains('started')) {
      return const Color(0xFF38BDF8);
    }
    if (s.contains('waiting') || s.contains('pending') || s.contains('queued')) {
      return const Color(0xFFFBBF24);
    }
    if (s.contains('cancelled')) {
      return const Color(0xFF94A3B8);
    }
    return const Color(0xFF38BDF8);
  }

  String _formatTime(DateTime dateTime) {
    final isEn = _isEnglish();
    final now = DateTime.now();
    final diff = now.difference(dateTime);

    if (diff.inMinutes < 60) {
      final mins = diff.inMinutes.clamp(1, 60);
      return isEn ? '${mins}m ago' : '$mins phút trước';
    } else if (diff.inHours < 24) {
      return isEn ? '${diff.inHours}h ago' : '${diff.inHours} giờ trước';
    } else if (diff.inDays < 7) {
      return isEn ? '${diff.inDays}d ago' : '${diff.inDays} ngày trước';
    } else {
      return '${dateTime.month}/${dateTime.day}';
    }
  }
}
