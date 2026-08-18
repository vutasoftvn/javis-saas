import 'package:flutter/material.dart';
import '../../../data/models/stage_model.dart';

class NextBestActionsCard extends StatefulWidget {
  final List<dynamic> actions;
  final StageContextModel? stageContext;
  final Function(String actionTitle, String? prompt) onExecuteWithAi;
  final Function(String actionTitle) onAddTo12Wy;
  final VoidCallback? onRefresh;
  final bool isCompact;

  const NextBestActionsCard({
    super.key,
    required this.actions,
    this.stageContext,
    required this.onExecuteWithAi,
    required this.onAddTo12Wy,
    this.onRefresh,
    this.isCompact = false,
  });

  @override
  State<NextBestActionsCard> createState() => _NextBestActionsCardState();
}

class _NextBestActionsCardState extends State<NextBestActionsCard> {
  bool _isExpanded = true;

  List<Map<String, dynamic>> _resolveEffectiveActions() {
    if (widget.actions.isEmpty) {
      return [];
    }
    return widget.actions.map((item) {
      if (item is Map<String, dynamic>) return item;
      return <String, dynamic>{
        'title': item.toString(),
        'reason': 'Hành động ưu tiên theo chính sách Stage',
        'priority': 'HIGH',
      };
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final actions = _resolveEffectiveActions().take(3).toList();
    if (actions.isEmpty) {
      return const SizedBox.shrink();
    }
    final stage = widget.stageContext?.projectStage ?? ProjectStage.s1ProblemValidation;

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E).withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: const Color(0xFF38BDF8).withValues(alpha: 0.3),
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header bar
            InkWell(
              onTap: () => setState(() => _isExpanded = !_isExpanded),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFF38BDF8).withValues(alpha: 0.12),
                      Colors.transparent,
                    ],
                  ),
                  border: Border(
                    bottom: BorderSide(
                      color: _isExpanded
                          ? const Color(0xFF38BDF8).withValues(alpha: 0.15)
                          : Colors.transparent,
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Icon(
                        Icons.bolt_rounded,
                        color: Color(0xFF38BDF8),
                        size: 15,
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text(
                        'Hành Động Ưu Tiên Tiếp Theo',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 12.5,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: stage.primaryColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '${actions.length} việc',
                        style: TextStyle(
                          color: stage.primaryColor,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      _isExpanded
                          ? Icons.keyboard_arrow_up_rounded
                          : Icons.keyboard_arrow_down_rounded,
                      color: const Color(0xFF94A3B8),
                      size: 18,
                    ),
                  ],
                ),
              ),
            ),

            // Content
            if (_isExpanded)
              Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  children: [
                    for (int i = 0; i < actions.length; i++)
                      _buildActionItem(actions[i], i, stage),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionItem(Map<String, dynamic> action, int index, ProjectStage stage) {
    final title = action['title']?.toString() ?? 'Hành động ưu tiên';
    final reason = action['reason']?.toString() ?? '';
    final prompt = action['prompt']?.toString();
    final isCritical = action['priority']?.toString().toUpperCase() == 'CRITICAL';

    return Container(
      margin: EdgeInsets.only(bottom: index < 2 ? 8 : 0),
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isCritical
              ? const Color(0xFFF59E0B).withValues(alpha: 0.35)
              : Colors.white.withValues(alpha: 0.08),
          width: 0.8,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                margin: const EdgeInsets.only(top: 2),
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                decoration: BoxDecoration(
                  color: isCritical
                      ? const Color(0xFFF59E0B).withValues(alpha: 0.2)
                      : const Color(0xFF38BDF8).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  isCritical ? 'P0' : 'P1',
                  style: TextStyle(
                    color: isCritical ? const Color(0xFFF59E0B) : const Color(0xFF38BDF8),
                    fontSize: 9.5,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
              ),
            ],
          ),
          if (reason.isNotEmpty) ...[
            const SizedBox(height: 5),
            Padding(
              padding: const EdgeInsets.only(left: 2),
              child: Text(
                '💡 $reason',
                style: const TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 10.5,
                  height: 1.3,
                ),
              ),
            ),
          ],
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              InkWell(
                onTap: () => widget.onAddTo12Wy(title),
                borderRadius: BorderRadius.circular(6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.calendar_today_outlined, size: 11, color: Color(0xFF94A3B8)),
                      SizedBox(width: 4),
                      Text(
                        '+ 12WY',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 10.5, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 6),
              InkWell(
                onTap: () => widget.onExecuteWithAi(title, prompt),
                borderRadius: BorderRadius.circular(6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF0284C7), Color(0xFF0369A1)],
                    ),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.auto_awesome, size: 11, color: Colors.white),
                      SizedBox(width: 4),
                      Text(
                        'AI Thực hiện',
                        style: TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.bold),
                      ),
                    ],
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
