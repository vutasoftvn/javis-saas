import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../data/models/execution_plan_model.dart';
import '../../../data/models/founder_decision_model.dart';

enum _TimelineEventType { chat, decision, approval, task, plan }

class _TimelineEvent {
  final _TimelineEventType type;
  final String title;
  final String? subtitle;
  final DateTime? time;

  const _TimelineEvent({
    required this.type,
    required this.title,
    this.subtitle,
    this.time,
  });
}

/// Card timeline gộp mọi tín hiệu hoạt động trong phiên làm việc hiện tại —
/// chat với Co-Founder, quyết định, phê duyệt, nhiệm vụ và execution plan —
/// vào một luồng duy nhất. `chatMessages`/`FounderInboxTask`/`ExecutionPlan`
/// chưa có timestamp ở tầng model nên thứ tự hiển thị dựa theo thứ tự chèn
/// (item mới nhất của mỗi nguồn đứng trước), không phải sort tuyệt đối theo
/// thời gian thực — đủ dùng cho mục đích "xem lại mọi thứ vừa xảy ra".
class HubActivityTimelineCard extends StatelessWidget {
  final List<Map<String, String>> chatMessages;
  final List<FounderDecisionModel> decisions;
  final List<Map<String, dynamic>> approvals;
  final List<FounderInboxTask> tasks;
  final List<ExecutionPlan> plans;

  const HubActivityTimelineCard({
    super.key,
    this.chatMessages = const [],
    this.decisions = const [],
    this.approvals = const [],
    this.tasks = const [],
    this.plans = const [],
  });

  List<_TimelineEvent> _buildEvents() {
    final events = <_TimelineEvent>[];

    for (final m in chatMessages.reversed.take(6)) {
      final isUser = m['role'] == 'user';
      final content = m['content'] ?? '';
      if (content.trim().isEmpty) continue;
      events.add(
        _TimelineEvent(
          type: _TimelineEventType.chat,
          title: isUser ? 'Founder' : 'Co-Founder AI',
          subtitle: content,
        ),
      );
    }

    for (final d in decisions.reversed) {
      events.add(
        _TimelineEvent(
          type: _TimelineEventType.decision,
          title: d.question,
          subtitle: d.domain,
          time: d.createdAt,
        ),
      );
    }

    for (final a in approvals.reversed) {
      events.add(
        _TimelineEvent(
          type: _TimelineEventType.approval,
          title: (a['title'] ?? 'Yêu cầu phê duyệt').toString(),
          subtitle: (a['agent_name'] ?? '').toString(),
        ),
      );
    }

    for (final t in tasks.reversed) {
      events.add(
        _TimelineEvent(
          type: _TimelineEventType.task,
          title: t.title,
          subtitle: t.status,
        ),
      );
    }

    for (final p in plans.reversed) {
      events.add(
        _TimelineEvent(
          type: _TimelineEventType.plan,
          title: p.goalText,
          subtitle: p.status,
        ),
      );
    }

    events.sort((a, b) {
      if (a.time == null && b.time == null) return 0;
      if (a.time == null) return 1;
      if (b.time == null) return -1;
      return b.time!.compareTo(a.time!);
    });

    return events;
  }

  @override
  Widget build(BuildContext context) {
    final events = _buildEvents();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.history_outlined, color: AppTheme.primaryLight, size: 18),
              const SizedBox(width: 8),
              const Text(
                'HOẠT ĐỘNG GẦN ĐÂY',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12.5,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (events.isEmpty)
            Text(
              'Chưa có hoạt động nào — chat, quyết định, phê duyệt và nhiệm vụ sẽ hiện tại đây.',
              style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 12),
            )
          else
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 420),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const ClampingScrollPhysics(),
                itemCount: events.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, index) => _buildEventRow(events[index]),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEventRow(_TimelineEvent event) {
    final meta = _metaFor(event.type);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: meta.color.withValues(alpha: 0.15),
            shape: BoxShape.circle,
          ),
          child: Icon(meta.icon, color: meta.color, size: 14),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: meta.color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      meta.label,
                      style: TextStyle(color: meta.color, fontSize: 9, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 3),
              Text(
                event.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w500),
              ),
              if (event.subtitle != null && event.subtitle!.trim().isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  event.subtitle!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 11),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  _EventMeta _metaFor(_TimelineEventType type) {
    switch (type) {
      case _TimelineEventType.chat:
        return _EventMeta(Icons.chat_bubble_outline, AppTheme.primary, 'CHAT');
      case _TimelineEventType.decision:
        return _EventMeta(Icons.gavel_outlined, const Color(0xFFF59E0B), 'DECISION');
      case _TimelineEventType.approval:
        return _EventMeta(Icons.shield_outlined, const Color(0xFF3B82F6), 'APPROVAL');
      case _TimelineEventType.task:
        return _EventMeta(Icons.task_alt_outlined, const Color(0xFF10B981), 'TASK');
      case _TimelineEventType.plan:
        return _EventMeta(Icons.route_outlined, const Color(0xFFEC4899), 'PLAN');
    }
  }
}

class _EventMeta {
  final IconData icon;
  final Color color;
  final String label;

  const _EventMeta(this.icon, this.color, this.label);
}
