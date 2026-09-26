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
          border: Border.all(color: const Color(0x336366F1)),
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
          border: Border.all(color: const Color(0x336366F1)),
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

    return Container(
      key: const Key('operating_week_card'),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0x336366F1)),
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
          if (week?.focus != null && week!.focus!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              week.focus!,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontStyle: FontStyle.italic,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
              ),
            ),
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
