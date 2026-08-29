import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import 'okr_key_result_item.dart';
import 'okr_dialogs.dart';

class OkrObjectiveCard extends StatelessWidget {
  final dynamic obj;
  final StrategyController controller;

  const OkrObjectiveCard({
    super.key,
    required this.obj,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    final objectiveId = obj['id']?.toString() ?? '';
    final progress = controller.calculateObjectiveProgress(objectiveId);
    final keyResults = controller.getKeyResultsForObjective(objectiveId);
    final status = (obj['status'] ?? 'active').toString();

    return Obx(() {
      final isExpanded = controller.expandedObjectiveId.value == objectiveId;

      return Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isExpanded ? AppTheme.primary : AppTheme.borderDark,
            width: isExpanded ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => controller.toggleObjectiveExpanded(objectiveId),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Text(
                            obj['title'] ?? 'Mục tiêu chiến lược',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                              height: 1.25,
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                '${keyResults.length} KR',
                                style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Tooltip(
                              message: 'Trạng thái: ${status.toUpperCase()}',
                              child: const Icon(
                                Icons.check_circle_rounded,
                                color: Color(0xFF10B981),
                                size: 16,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Icon(
                              isExpanded ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                              color: Colors.white70,
                              size: 20,
                            ),
                            const SizedBox(width: 4),
                            PopupMenuButton<String>(
                              icon: const Icon(Icons.more_vert_rounded, color: Colors.white54, size: 18),
                              color: AppTheme.surfaceDark,
                              itemBuilder: (ctx) => [
                                const PopupMenuItem(
                                  value: 'add_kr',
                                  child: Row(children: [Icon(Icons.add_chart_rounded, size: 16), SizedBox(width: 8), Text('Thêm Key Result')]),
                                ),
                                const PopupMenuItem(
                                  value: 'delete',
                                  child: Row(children: [Icon(Icons.delete_outline_rounded, color: AppTheme.accent, size: 16), SizedBox(width: 8), Text('Xóa Mục tiêu', style: TextStyle(color: AppTheme.accent))]),
                                ),
                              ],
                              onSelected: (val) {
                                if (val == 'add_kr') {
                                  OkrDialogs.showCreateKeyResultDialog(context, controller, objectiveId);
                                } else if (val == 'delete') {
                                  controller.deleteObjective(objectiveId);
                                }
                              },
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(6),
                            child: LinearProgressIndicator(
                              value: progress,
                              backgroundColor: Colors.white10,
                              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF818CF8)),
                              minHeight: 6,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          '${(progress * 100).toInt()}%',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF818CF8)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            if (isExpanded) ...[
              const Divider(color: Colors.white12, height: 1),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.checklist_rounded, size: 15, color: Color(0xFF818CF8)),
                            const SizedBox(width: 6),
                            Text(
                              'DANH SÁCH KEY RESULTS (${keyResults.length} KR):',
                              style: const TextStyle(color: Color(0xFF818CF8), fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        TextButton.icon(
                          onPressed: () => OkrDialogs.showCreateKeyResultDialog(context, controller, objectiveId),
                          icon: const Icon(Icons.add_rounded, size: 14),
                          label: const Text('Thêm KR', style: TextStyle(fontSize: 11)),
                          style: TextButton.styleFrom(
                            foregroundColor: const Color(0xFF818CF8),
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (keyResults.isNotEmpty)
                      ...keyResults.map(
                        (kr) => OkrKeyResultItem(
                          kr: kr,
                          controller: controller,
                          onCheckIn: () => OkrDialogs.showCheckinKeyResultDialog(context, controller, kr),
                        ),
                      )
                    else
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.03),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'Chưa có Key Result nào cho Mục tiêu này. Bấm "+ Thêm KR" để bổ sung.',
                          style: TextStyle(color: Colors.white54, fontSize: 12),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ],
        ),
      );
    });
  }
}
