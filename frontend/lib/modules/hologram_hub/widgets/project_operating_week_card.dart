import '../../../core/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../projects/models/project_operating_loop.dart';

/// Task 4 (2026-09-14 remediation) — trước đây widget này tự tính
/// "currentWeek" từ `cycle.startDate` rồi tìm trong `cycle.weeklyPlans[]`
/// (hình dạng không tồn tại ở backend thật). Server đã trả `currentWeek`
/// (field số nguyên trên `CycleDto`) và `currentWeek` (đối tượng tuần, field
/// gốc sibling của `activeCycle`) — dùng thẳng, không tự suy diễn nữa.
class ProjectOperatingWeekCard extends StatelessWidget {
  const ProjectOperatingWeekCard({
    super.key,
    required this.operatingLoop,
    this.isLoading = false,
    this.errorMessage,
    this.onRetry,
  });

  final ProjectOperatingLoop? operatingLoop;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onRetry;

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isEn = _isEnglish();

    if (isLoading) {
      return Container(
        key: const Key('operating_week_loading'),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A).withValues(alpha: 0.38),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
        ),
        child: const Center(
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    if (errorMessage != null && errorMessage!.isNotEmpty) {
      return Container(
        key: const Key('operating_week_error'),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: theme.colorScheme.errorContainer.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: theme.colorScheme.error.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.error_outline, color: theme.colorScheme.error),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    isEn ? 'Error loading operating cycle' : 'Lỗi tải chu kỳ hoạt động',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.error,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              errorMessage!,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface,
              ),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                key: const Key('operating_week_retry_button'),
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 16),
                label: Text(isEn ? 'Retry' : 'Thử lại'),
              ),
            ],
          ],
        ),
      );
    }

    final cycle = operatingLoop?.activeCycle;
    if (cycle == null) {
      return Container(
        key: const Key('operating_week_no_cycle'),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A).withValues(alpha: 0.38),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.calendar_today_outlined,
                    size: 20, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    isEn ? 'Project Operating Cycle' : 'Chu kỳ hoạt động dự án',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              isEn
                  ? 'No active operating cycle for this project.'
                  : 'Dự án chưa có chu kỳ hoạt động (Operating Cycle) nào đang diễn ra.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
              ),
            ),
          ],
        ),
      );
    }

    final currentWeekNo = cycle.currentWeek;
    final week = operatingLoop?.currentWeek;
    final commitments = week == null
        ? const <LoopCommitment>[]
        : (operatingLoop?.commitments ?? [])
            .where((c) => c.weeklyPlanId == week.id)
            .toList();
    final tasks = operatingLoop?.tasks ?? [];

    // Tìm Objective và danh sách Key Results (KR) tương ứng
    final objectives = operatingLoop?.objectives ?? [];
    LoopObjectiveTree? currentObjective;
    if (cycle.sourceObjectiveId != null) {
      currentObjective = objectives.firstWhereOrNull(
        (o) => o.objective.id == cycle.sourceObjectiveId,
      );
    }
    currentObjective ??= objectives.firstWhereOrNull((o) {
      final objTitle = o.objective.title.trim().toLowerCase();
      final focus = (week?.focus ?? '').trim().toLowerCase();
      return focus.isNotEmpty && (focus.contains(objTitle) || objTitle.contains(focus));
    });
    currentObjective ??= objectives.firstOrNull;

    final keyResultTrees = currentObjective != null && currentObjective.keyResults.isNotEmpty
        ? currentObjective.keyResults
        : objectives.expand((o) => o.keyResults).toList();

    // Tách P0 / giai đoạn làm title riêng nếu có dạng [P0 - ...] hoặc [P...]
    final focusText = (week?.focus ?? '').trim();
    String? phaseTitle;
    String? focusBody;

    if (focusText.isNotEmpty) {
      final match = RegExp(r'^\[(.*?)\]\s*(.*)$', dotAll: true).firstMatch(focusText);
      if (match != null) {
        phaseTitle = match.group(1)?.trim();
        focusBody = match.group(2)?.trim();
      } else {
        focusBody = focusText;
      }
    }

    return Container(
      key: const Key('operating_week_card'),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    Icon(Icons.calendar_today,
                        size: 20, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        isEn
                            ? 'Cycle: ${cycle.durationWeeks} weeks — Week $currentWeekNo'
                            : 'Chu kỳ ${cycle.durationWeeks} tuần — Tuần $currentWeekNo',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  isEn
                      ? 'Week $currentWeekNo / ${cycle.durationWeeks}'
                      : 'Tuần $currentWeekNo / ${cycle.durationWeeks}',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          if (phaseTitle != null && phaseTitle.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: AppTheme.primary.withValues(alpha: 0.35),
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.flag_circle_outlined,
                        size: 15,
                        color: AppTheme.primaryLight,
                      ),
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          phaseTitle,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: AppTheme.primaryLight,
                            fontWeight: FontWeight.bold,
                            fontSize: 12.5,
                            letterSpacing: 0.2,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
          if (focusBody != null && focusBody.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              focusBody,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontStyle: phaseTitle == null ? FontStyle.italic : FontStyle.normal,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.85),
                height: 1.45,
              ),
            ),
          ],
          if (keyResultTrees.isNotEmpty) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Icon(Icons.track_changes, size: 16, color: AppTheme.primaryLight),
                const SizedBox(width: 6),
                Text(
                  isEn ? 'Key Results (KR):' : 'Kết quả then chốt (Key Results):',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.75),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...keyResultTrees.map((krTree) {
              final kr = krTree.keyResult;
              final title = (kr.title ?? '').trim();
              final hasMetrics = kr.targetValue != null && kr.targetValue! > 0;
              final current = kr.currentValue ?? 0.0;
              final target = kr.targetValue ?? 0.0;
              final unit = kr.unit ?? '';
              final progress = hasMetrics && target > 0 ? (current / target).clamp(0.0, 1.0) : null;
              final isCompleted = kr.status == 'done' || kr.status == 'completed' || (progress != null && progress >= 1.0);
              final unitLower = unit.toLowerCase();
              final isBinaryVerification = (target <= 1.0) || unitLower.contains('kiểm chứng') || kr.scoringType.toUpperCase() == 'BOOLEAN';

              return Padding(
                padding: const EdgeInsets.only(bottom: 6.0),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AppTheme.primary.withValues(alpha: 0.18),
                      width: 1,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(top: 2.0),
                            child: Icon(
                              isCompleted ? Icons.check_circle : Icons.radio_button_unchecked,
                              size: 15,
                              color: isCompleted ? Colors.green : AppTheme.primaryLight,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              title.isNotEmpty ? title : (isEn ? 'Key Result' : 'Kết quả then chốt'),
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w500,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          if (isBinaryVerification)
                            Tooltip(
                              message: isCompleted
                                  ? (isEn ? 'Verified' : 'Đã kiểm chứng')
                                  : (isEn ? 'Pending' : 'Chưa kiểm chứng'),
                              child: Container(
                                padding: const EdgeInsets.all(5),
                                decoration: BoxDecoration(
                                  color: isCompleted
                                      ? Colors.green.withValues(alpha: 0.15)
                                      : Colors.white.withValues(alpha: 0.06),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                    color: isCompleted
                                        ? Colors.green.withValues(alpha: 0.35)
                                        : Colors.white.withValues(alpha: 0.15),
                                    width: 1,
                                  ),
                                ),
                                child: Icon(
                                  isCompleted ? Icons.verified : Icons.hourglass_empty_rounded,
                                  size: 13,
                                  color: isCompleted ? Colors.green : const Color(0xFF94A3B8),
                                ),
                              ),
                            )
                          else if (hasMetrics)
                            Text(
                              '${current.toStringAsFixed(current.truncateToDouble() == current ? 0 : 1)} / ${target.toStringAsFixed(target.truncateToDouble() == target ? 0 : 1)}${unit.isNotEmpty ? ' $unit' : ''}',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: AppTheme.primaryLight,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                        ],
                      ),
                      if (!isBinaryVerification && progress != null) ...[
                        const SizedBox(height: 6),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: progress,
                            minHeight: 4,
                            backgroundColor: AppTheme.primary.withValues(alpha: 0.12),
                            valueColor: AlwaysStoppedAnimation<Color>(
                              isCompleted ? Colors.green : AppTheme.primary,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }),
          ],
          const SizedBox(height: 16),
          if (commitments.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8.0),
              child: Text(
                isEn
                    ? 'No commitments scheduled for this week.'
                    : 'Chưa có cam kết công việc nào trong tuần này.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                ),
              ),
            )
          else ...[
            Text(
              isEn ? 'Commitments this week:' : 'Cam kết tuần này:',
              style: theme.textTheme.labelMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            ...commitments.map((commitment) {
              final commitmentTasks =
                  tasks.where((t) => t.weeklyCommitmentId == commitment.id).toList();
              final totalTasks = commitmentTasks.length;
              final incompleteTasks = commitmentTasks
                  .where((t) => t.status != 'done' && t.status != 'completed')
                  .length;

              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          commitment.title,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w500,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        isEn
                            ? '$incompleteTasks/$totalTasks tasks'
                            : '$incompleteTasks/$totalTasks việc',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: incompleteTasks > 0
                              ? theme.colorScheme.primary
                              : Colors.green,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ],
        ],
      ),
    );
  }
}
