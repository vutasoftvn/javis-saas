import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/theme/app_theme.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/project_operating_setup_model.dart';

class Top3FocusWidget extends StatelessWidget {
  final List<NextBestActionModel> actions;
  final Function(NextBestActionModel) onActionTap;
  final List<FirstWeekActionDraft> firstWeekActions;
  final ValueChanged<FirstWeekActionDraft>? onToggleActionStatus;
  final void Function(FirstWeekActionDraft action, DateTime? plannedStartAt)?
      onScheduleAction;
  final VoidCallback? onDiscuss;
  final VoidCallback? onOpenProjectLoop;
  final VoidCallback? onOpenProjectAnalysis;
  final bool showDescription;

  const Top3FocusWidget({
    super.key,
    required this.actions,
    required this.onActionTap,
    this.firstWeekActions = const [],
    this.onToggleActionStatus,
    this.onScheduleAction,
    this.onDiscuss,
    this.onOpenProjectLoop,
    this.onOpenProjectAnalysis,
    this.showDescription = false,
  });

  @override
  Widget build(BuildContext context) {
    final hasNextBestActions = actions.isNotEmpty;
    final hasFirstWeekActions = firstWeekActions.isNotEmpty;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                hasNextBestActions ? Icons.stars : Icons.stars_outlined,
                color: const Color(0xFFF59E0B),
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  L10nKey.hubTop3Title.tr,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 0.5,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (hasNextBestActions) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.info.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'Next Best Actions',
                    style: TextStyle(fontSize: 11, color: AppTheme.info, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 12),
          if (hasNextBestActions)
            ...actions.asMap().entries.map((entry) {
              final idx = entry.key + 1;
              final item = entry.value;
              return _buildActionCard(idx, item);
            })
          else ...[
            if (showDescription) ...[
              Text(
                L10nKey.hubTop3Empty.tr,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (onOpenProjectAnalysis != null) ...[
              Wrap(
                spacing: 12,
                runSpacing: 10,
                children: [
                  ElevatedButton.icon(
                    onPressed: onOpenProjectAnalysis,
                    icon: const Icon(Icons.psychology_alt_rounded, size: 16),
                    label: _buildAnalyzeButtonLabel(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.success,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      textStyle: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
          if (hasFirstWeekActions) ...[
            const SizedBox(height: 20),
            const Divider(color: Color(0xFF334155), height: 1),
            const SizedBox(height: 16),
            Text(
              L10nKey.hubFirstWeekActionsTitle.tr,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: Colors.white,
                letterSpacing: 0.3,
              ),
            ),
            const SizedBox(height: 10),
            ...firstWeekActions.map((action) => _buildChecklistItem(context, action)),
          ],
        ],
      ),
    );
  }

  Widget _buildChecklistItem(BuildContext context, FirstWeekActionDraft action) {
    final isDone = action.isDone;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Checkbox(
            value: isDone,
            activeColor: const Color(0xFF10B981),
            onChanged: onToggleActionStatus == null
                ? null
                : (_) => onToggleActionStatus!(action),
          ),
          Expanded(
            child: Text(
              action.title,
              style: TextStyle(
                color: isDone ? Colors.white.withValues(alpha: 0.5) : Colors.white,
                fontSize: 13.5,
                decoration: isDone ? TextDecoration.lineThrough : null,
              ),
            ),
          ),
          InkWell(
            onTap: onScheduleAction == null ? null : () => _pickSchedule(context, action),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.schedule, size: 13, color: Color(0xFF94A3B8)),
                  const SizedBox(width: 4),
                  Text(
                    action.plannedStartAt != null
                        ? _formatScheduleBadge(context, action.plannedStartAt!)
                        : L10nKey.hubActionNoTimeSet.tr,
                    style: const TextStyle(fontSize: 11.5, color: Color(0xFF94A3B8)),
                  ),
                  // Fix 4 (final review) — trước đây chỉ có thể ĐẶT giờ, không
                  // thể XOÁ lịch đã đặt từ UI dù backend hỗ trợ đầy đủ.
                  if (action.plannedStartAt != null && onScheduleAction != null) ...[
                    const SizedBox(width: 4),
                    InkWell(
                      onTap: () => onScheduleAction!(action, null),
                      borderRadius: BorderRadius.circular(6),
                      child: const Padding(
                        padding: EdgeInsets.all(2),
                        child: Icon(Icons.close, size: 12, color: Color(0xFF94A3B8)),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Hiện "hôm nay lúc 14:00" chỉ với giờ, nhưng "8/9 14:00" cho ngày khác —
  /// nếu không, "hôm nay 14:00" và "thứ Sáu tuần sau 14:00" render giống hệt
  /// nhau, founder không phân biệt được lịch đang đặt cho ngày nào.
  String _formatScheduleBadge(BuildContext context, DateTime plannedStartAt) {
    final local = plannedStartAt.toLocal();
    final now = DateTime.now();
    final time = TimeOfDay.fromDateTime(local).format(context);
    final isToday = local.year == now.year && local.month == now.month && local.day == now.day;
    return isToday ? time : '${local.day}/${local.month} $time';
  }

  Future<void> _pickSchedule(BuildContext context, FirstWeekActionDraft action) async {
    final now = DateTime.now();
    // Fix 2 (final review) — "Hành động tuần đầu" sống trong cửa sổ 2-4
    // tuần, nên `plannedStartAt` cũ hơn `now - 1 ngày` là bình thường; không
    // clamp thì `showDatePicker` ném assert vì initialDate < firstDate.
    final firstDate = now.subtract(const Duration(days: 1));
    final rawInitialDate = action.plannedStartAt?.toLocal() ?? now;
    final initialDate = rawInitialDate.isBefore(firstDate) ? firstDate : rawInitialDate;
    final date = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: firstDate,
      lastDate: now.add(const Duration(days: 90)),
    );
    if (date == null || !context.mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initialDate),
    );
    if (time == null) return;
    final picked = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    onScheduleAction?.call(action, picked);
  }

  Widget _buildActionCard(int index, NextBestActionModel item) {
    Color tagColor;
    String tagLabel = item.category;

    switch (item.category) {
      case 'DECISION':
        tagColor = const Color(0xFFF59E0B);
        tagLabel = L10nKey.hubActionCategoryDecision.tr;
        break;
      case 'EXPERIMENT':
        tagColor = const Color(0xFFEC4899);
        tagLabel = L10nKey.hubActionCategoryExperiment.tr;
        break;
      case 'MISSION':
        tagColor = AppTheme.secondary;
        tagLabel = 'Mission';
        break;
      default:
        tagColor = const Color(0xFF10B981);
        tagLabel = L10nKey.hubActionCategoryAction.tr;
    }

    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFF334155), width: 1),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => onActionTap(item),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  shape: BoxShape.circle,
                  border: Border.all(color: const Color(0xFF475569)),
                ),
                child: Text(
                  '$index',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: tagColor.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            tagLabel,
                            style: TextStyle(fontSize: 10, color: tagColor, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            item.domain,
                            style: TextStyle(fontSize: 10, color: Colors.white.withValues(alpha: 0.4), fontWeight: FontWeight.w500),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      item.title,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      item.rationale,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.white.withValues(alpha: 0.65),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.arrow_forward_ios, color: Color(0xFF64748B), size: 14),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAnalyzeButtonLabel() {
    if (Get.isRegistered<LocaleController>()) {
      return Obx(() {
        final isEn =
            Get.find<LocaleController>().current.value == SupportedLocale.enUS;
        return Text(
          isEn
              ? 'Analyze & Plan First Week'
              : 'Phân tích & Lập Kế hoạch Tuần',
        );
      });
    }
    final isEn = Get.locale?.languageCode == 'en';
    return Text(
      isEn
          ? 'Analyze & Plan First Week'
          : 'Phân tích & Lập Kế hoạch Tuần',
    );
  }
}
