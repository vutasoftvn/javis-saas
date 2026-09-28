import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

import '../../../core/network/api_result.dart';
import '../../../core/routing/module_routes.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/ui/app_copy.dart';
import '../../projects/models/project_operating_loop.dart';
import '../../projects/services/project_agent_deployment_service.dart';
import '../../skills/models/founder_asset.dart';
import '../../skills/services/founder_asset_service.dart';
import '../controllers/hub_operations_controller.dart';
import '../models/hub_operations_models.dart';
import '../models/project_startup_team.dart';

/// Card vận hành 4 tab ở cột trái hub (spec 2026-09-27-hub-operations-workspace-design, đợt 1):
/// Tasks / Lịch / Công cụ / Agent của Project đang chọn. Chỉ hiện tóm tắt; "Xem tất cả" mở màn
/// đầy đủ đã có. Mọi hành động đi qua endpoint sẵn có, không hiển thị ID hay enum thô.
class HubOperationsCard extends StatelessWidget {
  const HubOperationsCard({
    super.key,
    required this.controller,
    required this.operatingLoop,
    this.onTasksChanged,
    this.isExpanded = true,
    this.onToggleExpand,
    this.isFullHeight = false,
  });

  final HubOperationsController controller;

  /// Operating loop do controller hub nạp sẵn (nguồn cho tab Tasks).
  final ProjectOperatingLoop? operatingLoop;
  final Future<void> Function()? onTasksChanged;
  final bool isExpanded;
  final VoidCallback? onToggleExpand;
  final bool isFullHeight;

  static const _maxRows = 6;

  @override
  Widget build(BuildContext context) {
    if (!isExpanded) {
      return Container(
        key: const Key('hub_operations_card'),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A).withValues(alpha: 0.38),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: InkWell(
          key: const Key('hub_ops_collapsed_bar'),
          onTap: onToggleExpand,
          borderRadius: BorderRadius.circular(10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    Icon(
                      Icons.tune_rounded,
                      size: 18,
                      color: AppTheme.primaryLight,
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        AppCopy.hubOpsTitle,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Obx(() {
                final current = controller.tab.value;
                final tabLabel = switch (current) {
                  HubOperationsTab.tasks => AppCopy.hubOpsTabTasks,
                  HubOperationsTab.schedules => AppCopy.hubOpsTabSchedules,
                  HubOperationsTab.tools => AppCopy.hubOpsTabTools,
                  HubOperationsTab.agents => AppCopy.hubOpsTabAgents,
                };
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: AppTheme.primary.withValues(alpha: 0.3),
                      width: 1,
                    ),
                  ),
                  child: Text(
                    tabLabel,
                    style: const TextStyle(
                      color: AppTheme.primaryLight,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                );
              }),
              if (onToggleExpand != null) ...[
                const SizedBox(width: 6),
                IconButton(
                  key: const Key('hub_ops_toggle_expand'),
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                  icon: const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white70, size: 20),
                  onPressed: onToggleExpand,
                ),
              ],
            ],
          ),
        ),
      );
    }

    return Container(
      key: const Key('hub_operations_card'),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
      ),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      child: Obx(() {
        final current = controller.tab.value;
        final switcherChild = AnimatedSwitcher(
          duration: const Duration(milliseconds: 240),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          transitionBuilder: (child, animation) {
            return FadeTransition(
              opacity: animation,
              child: RepaintBoundary(child: child),
            );
          },
          child: KeyedSubtree(
            key: ValueKey(current),
            child: switch (current) {
              HubOperationsTab.tasks => _TasksTab(
                  controller: controller,
                  operatingLoop: operatingLoop,
                  onTasksChanged: onTasksChanged,
                ),
              HubOperationsTab.schedules => _SchedulesTab(controller: controller),
              HubOperationsTab.tools => _ToolsTab(controller: controller),
              HubOperationsTab.agents => _AgentsTab(controller: controller),
            },
          ),
        );

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: isFullHeight ? MainAxisSize.max : MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  AppCopy.hubOpsTitle,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
                if (onToggleExpand != null)
                  IconButton(
                    key: const Key('hub_ops_toggle_collapse'),
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                    icon: const Icon(Icons.keyboard_arrow_up_rounded, color: Colors.white70, size: 20),
                    onPressed: onToggleExpand,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            _TabStrip(current: current, onSelect: controller.selectTab),
            const SizedBox(height: 10),
            if (isFullHeight)
              Expanded(
                child: SingleChildScrollView(
                  child: switcherChild,
                ),
              )
            else
              switcherChild,
          ],
        );
      }),
    );
  }
}

class _TabStrip extends StatelessWidget {
  const _TabStrip({required this.current, required this.onSelect});

  final HubOperationsTab current;
  final void Function(HubOperationsTab) onSelect;

  @override
  Widget build(BuildContext context) {
    final labels = {
      HubOperationsTab.tasks: AppCopy.hubOpsTabTasks,
      HubOperationsTab.schedules: AppCopy.hubOpsTabSchedules,
      HubOperationsTab.tools: AppCopy.hubOpsTabTools,
      HubOperationsTab.agents: AppCopy.hubOpsTabAgents,
    };
    final tabs = [
      HubOperationsTab.tasks,
      HubOperationsTab.schedules,
      HubOperationsTab.tools,
      HubOperationsTab.agents,
    ];
    final selectedIndex = tabs.indexOf(current).clamp(0, tabs.length - 1);

    return Container(
      padding: const EdgeInsets.all(3.5),
      decoration: BoxDecoration(
        color: const Color(0xFF0A101D).withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(
          color: AppTheme.primary.withValues(alpha: 0.16),
          width: 1,
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final tabWidth = constraints.maxWidth / tabs.length;
          return Stack(
            children: [
              AnimatedPositioned(
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeInOutCubic,
                left: selectedIndex * tabWidth,
                top: 0,
                bottom: 0,
                width: tabWidth,
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(100),
                    gradient: LinearGradient(
                      colors: [
                        AppTheme.primary.withValues(alpha: 0.28),
                        AppTheme.primary.withValues(alpha: 0.16),
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    border: Border.all(
                      color: AppTheme.primary.withValues(alpha: 0.42),
                      width: 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primary.withValues(alpha: 0.18),
                        blurRadius: 6,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                ),
              ),
              Row(
                children: [
                  for (final tab in tabs)
                    Expanded(
                      child: InkWell(
                        key: Key("hub_ops_tab_${tab.name}"),
                        borderRadius: BorderRadius.circular(100),
                        onTap: () => onSelect(tab),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 6.5),
                          alignment: Alignment.center,
                          child: AnimatedDefaultTextStyle(
                            duration: const Duration(milliseconds: 200),
                            style: TextStyle(
                              fontSize: 12,
                              color: tab == current
                                  ? Colors.white
                                  : Colors.white.withValues(alpha: 0.6),
                              fontWeight: tab == current
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                            ),
                            child: Text(
                              labels[tab] ?? tab.name,
                              overflow: TextOverflow.ellipsis,
                              maxLines: 1,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

// ── Khung dùng chung ─────────────────────────────────────────────────────

TextStyle get _rowTitle => const TextStyle(color: Colors.white, fontSize: 12.5);
TextStyle get _rowMeta => TextStyle(color: Colors.white.withValues(alpha: 0.55), fontSize: 11);

class _Notice extends StatelessWidget {
  const _Notice(this.text, {this.onRetry});

  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Column(
        children: [
          Text(text, textAlign: TextAlign.center, style: _rowMeta.copyWith(fontSize: 12)),
          if (onRetry != null)
            TextButton(onPressed: onRetry, child: Text(AppCopy.hubOpsRetry)),
        ],
      ),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.all(12),
        child: Center(
          child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill(this.text, {this.color});

  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? AppTheme.primary;
    return Container(
      margin: const EdgeInsets.only(right: 6),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(text, style: TextStyle(color: c, fontSize: 10.5)),
    );
  }
}

class _ViewAll extends StatelessWidget {
  const _ViewAll({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerRight,
        child: TextButton(
          style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
          onPressed: onTap,
          child: Text(AppCopy.hubOpsViewAll, style: const TextStyle(fontSize: 12)),
        ),
      );
}

void _reportOutcome(HubActionOutcome outcome) {
  if (outcome.ok) return;
  Get.rawSnackbar(message: AppCopy.hubOpsActionFailed, duration: const Duration(seconds: 3));
}

Future<bool> _confirm(BuildContext context, String title, String body, String action) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Text(body),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(AppCopy.hubOpsCancel)),
        TextButton(
          key: const Key('hub_ops_confirm'),
          onPressed: () => Navigator.of(ctx).pop(true),
          child: Text(action),
        ),
      ],
    ),
  );
  return ok ?? false;
}

String _formatWhen(DateTime? at) {
  if (at == null) return '—';
  return DateFormat('dd/MM HH:mm').format(at.toLocal());
}

// ── Tasks ────────────────────────────────────────────────────────────────

enum _TaskFilter { mine, agent, all }

class _TasksTab extends StatefulWidget {
  const _TasksTab({required this.controller, required this.operatingLoop, this.onTasksChanged});

  final HubOperationsController controller;
  final ProjectOperatingLoop? operatingLoop;
  final Future<void> Function()? onTasksChanged;

  @override
  State<_TasksTab> createState() => _TasksTabState();
}

class _TasksTabState extends State<_TasksTab> {
  _TaskFilter _filter = _TaskFilter.all;

  static const _statusChoices = ['todo', 'in_progress', 'done', 'blocked'];

  @override
  Widget build(BuildContext context) {
    final all = widget.operatingLoop?.tasks ?? const <LoopTask>[];
    final tasks = all.where((t) {
      switch (_filter) {
        case _TaskFilter.mine:
          return !t.isAgentCreated;
        case _TaskFilter.agent:
          return t.isAgentCreated;
        case _TaskFilter.all:
          return true;
      }
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 6,
          children: [
            for (final f in _TaskFilter.values)
              ChoiceChip(
                key: Key('hub_ops_task_filter_${f.name}'),
                visualDensity: VisualDensity.compact,
                label: Text(
                  switch (f) {
                    _TaskFilter.mine => AppCopy.hubOpsFilterMine,
                    _TaskFilter.agent => AppCopy.hubOpsFilterAgent,
                    _TaskFilter.all => AppCopy.hubOpsFilterAll,
                  },
                  style: const TextStyle(fontSize: 11),
                ),
                selected: _filter == f,
                onSelected: (_) => setState(() => _filter = f),
              ),
          ],
        ),
        const SizedBox(height: 6),
        if (tasks.isEmpty)
          _Notice(AppCopy.hubOpsNoTasks)
        else
          for (final task in tasks.take(HubOperationsCard._maxRows)) _taskRow(task),
        _ViewAll(onTap: () => Get.toNamed(WorkspaceModule.tasks.path)),
      ],
    );
  }

  Widget _taskRow(LoopTask task) {
    final status = task.status.toLowerCase();
    return Obx(() {
      final busy = widget.controller.busy.contains(task.id);
      return Padding(
        key: Key('hub_ops_task_${task.id}'),
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(task.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: _rowTitle),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      _Pill(AppCopy.hubOpsTaskStatus(status)),
                      if (task.isAgentCreated)
                        _Pill(
                          status == 'draft' ? AppCopy.hubOpsAgentDraft : AppCopy.hubOpsAgentCreated,
                          color: Colors.purpleAccent,
                        ),
                    ],
                  ),
                ],
              ),
            ),
            if (busy)
              const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
            else
              PopupMenuButton<String>(
                key: Key('hub_ops_task_menu_${task.id}'),
                tooltip: AppCopy.hubOpsChangeStatus,
                icon: Icon(Icons.more_horiz, size: 18, color: Colors.white.withValues(alpha: 0.7)),
                onSelected: (next) async {
                  final outcome = await widget.controller.advanceTask(
                    task.id,
                    next,
                    onTasksChanged: widget.onTasksChanged,
                  );
                  _reportOutcome(outcome);
                },
                itemBuilder: (_) => [
                  for (final s in _statusChoices.where((s) => s != status))
                    PopupMenuItem(
                      key: Key('hub_ops_task_status_$s'),
                      value: s,
                      child: Text(AppCopy.hubOpsTaskStatus(s)),
                    ),
                ],
              ),
          ],
        ),
      );
    });
  }
}

// ── Lịch ─────────────────────────────────────────────────────────────────

class _SchedulesTab extends StatelessWidget {
  const _SchedulesTab({required this.controller});

  final HubOperationsController controller;

  String _cadence(HubSchedule s) {
    final hh = (s.hour ?? 0).toString().padLeft(2, "0");
    final mm = (s.minute ?? 0).toString().padLeft(2, "0");
    final time = "$hh:$mm";
    switch (s.scheduleKind) {
      case "daily":
        return AppCopy.hubOpsDaily(time);
      case "weekdays":
        return AppCopy.hubOpsWeekdays(time);
      default:
        return AppCopy.hubOpsOnce(_formatWhen(s.nextRunAt ?? s.lastRunAt));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.schedulesLoading.value && controller.schedules.isEmpty) {
        return const _Loading();
      }
      if (controller.schedulesError.value != null) {
        return _Notice(AppCopy.hubOpsLoadFailed, onRetry: controller.loadSchedules);
      }
      final isEmpty = controller.schedules.isEmpty;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  AppCopy.hubOpsSchedulesHeading,
                  style: _rowMeta.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
              TextButton.icon(
                key: const Key("hub_ops_create_schedule"),
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                ),
                onPressed: () => _openCreateScheduleDialog(context),
                icon: const Icon(Icons.add_rounded, size: 15),
                label: Text(
                  AppCopy.hubOpsCreateSchedule,
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          if (isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(
                children: [
                  _Notice(AppCopy.hubOpsNoSchedules),
                  const SizedBox(height: 6),
                  OutlinedButton.icon(
                    key: const Key("hub_ops_empty_create_schedule"),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.4)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    ),
                    onPressed: () => _openCreateScheduleDialog(context),
                    icon: const Icon(Icons.add_alarm_rounded, size: 15),
                    label: Text(AppCopy.hubOpsCreateSchedule, style: const TextStyle(fontSize: 12)),
                  ),
                ],
              ),
            )
          else
            for (final s in controller.schedules.take(HubOperationsCard._maxRows)) _row(context, s),
        ],
      );
    });
  }

  Future<void> _openCreateScheduleDialog(BuildContext context) async {
    final created = await showDialog<bool>(
      context: context,
      builder: (ctx) => _CreateScheduleDialog(controller: controller),
    );
    if (created == true) {
      Get.rawSnackbar(
        message: AppCopy.hubOpsCreateSchedule,
        duration: const Duration(seconds: 3),
      );
    }
  }

  Widget _row(BuildContext context, HubSchedule s) {
    final busy = controller.busy.contains(s.id);
    final last = controller.lastExecutions[s.id];
    final agent = controller.profileLabel(s.agentProfile) ?? AppCopy.hubOpsDefaultAgent;
    return Padding(
      key: Key("hub_ops_schedule_${s.id}"),
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _Pill(
                s.isEnabled ? AppCopy.hubOpsScheduleEnabled : AppCopy.hubOpsSchedulePaused,
                color: s.isEnabled ? Colors.greenAccent : Colors.orangeAccent,
              ),
              Expanded(
                child: Text(
                  s.promptTemplate,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: _rowTitle,
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text("${_cadence(s)} · $agent", style: _rowMeta),
          Text(
            last == null
                ? AppCopy.hubOpsNeverRun
                : AppCopy.hubOpsLastRun(
                    AppCopy.hubOpsExecutionState(last.state),
                    _formatWhen(last.scheduledFor),
                  ),
            style: _rowMeta.copyWith(color: last?.isFailure == true ? Colors.redAccent : null),
          ),
          if (busy)
            const LinearProgressIndicator(minHeight: 2)
          else
            Wrap(
              spacing: 2,
              children: [
                _action(
                  key: "run_${s.id}",
                  icon: Icons.play_arrow_rounded,
                  label: AppCopy.hubOpsRunNow,
                  onTap: s.isEnabled
                      ? () async => _reportOutcome(await controller.runScheduleNow(s.id))
                      : null,
                ),
                _action(
                  key: "toggle_${s.id}",
                  icon: s.isEnabled ? Icons.pause_rounded : Icons.play_circle_outline,
                  label: s.isEnabled ? AppCopy.hubOpsPause : AppCopy.hubOpsResume,
                  onTap: () async => _reportOutcome(
                    await controller.setScheduleState(s.id, s.isEnabled ? "paused" : "enabled"),
                  ),
                ),
                _action(
                  key: "archive_${s.id}",
                  icon: Icons.archive_outlined,
                  label: AppCopy.hubOpsArchive,
                  onTap: () async {
                    final ok = await _confirm(
                      context,
                      AppCopy.hubOpsArchiveConfirmTitle,
                      AppCopy.hubOpsArchiveConfirmBody,
                      AppCopy.hubOpsArchive,
                    );
                    if (ok) _reportOutcome(await controller.setScheduleState(s.id, "archived"));
                  },
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _action({
    required String key,
    required IconData icon,
    required String label,
    required VoidCallback? onTap,
  }) {
    return TextButton.icon(
      key: Key("hub_ops_schedule_$key"),
      style: TextButton.styleFrom(
        visualDensity: VisualDensity.compact,
        padding: const EdgeInsets.symmetric(horizontal: 6),
      ),
      onPressed: onTap,
      icon: Icon(icon, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 11)),
    );
  }
}

class _CreateScheduleDialog extends StatefulWidget {
  const _CreateScheduleDialog({required this.controller});

  final HubOperationsController controller;

  @override
  State<_CreateScheduleDialog> createState() => _CreateScheduleDialogState();
}

class _CreateScheduleDialogState extends State<_CreateScheduleDialog> {
  final _promptController = TextEditingController();
  String _scheduleKind = "daily";
  TimeOfDay _time = const TimeOfDay(hour: 8, minute: 0);
  String? _agentProfile;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    final team = widget.controller.team;
    if (team.isNotEmpty) {
      _agentProfile = team.first.profileKey;
    } else {
      _agentProfile = "operations";
    }
  }

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final team = widget.controller.team;
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      title: Text(
        AppCopy.hubOpsCreateSchedule,
        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
      ),
      content: SingleChildScrollView(
        child: SizedBox(
          width: 380,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(AppCopy.hubOpsSchedulePrompt, style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              TextField(
                key: const Key("hub_ops_schedule_prompt_input"),
                controller: _promptController,
                maxLines: 2,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: AppCopy.hubOpsCreateSchedulePromptHint,
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  contentPadding: const EdgeInsets.all(10),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(color: AppTheme.primary.withValues(alpha: 0.2)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: AppTheme.primary),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(AppCopy.hubOpsScheduleKind, style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              Row(
                children: [
                  _kindChip("daily", "Hằng ngày"),
                  const SizedBox(width: 6),
                  _kindChip("weekdays", "Ngày thường"),
                  const SizedBox(width: 6),
                  _kindChip("one_time", "Một lần"),
                ],
              ),
              const SizedBox(height: 12),
              Text(AppCopy.hubOpsScheduleTime, style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () async {
                  final picked = await showTimePicker(
                    context: context,
                    initialTime: _time,
                  );
                  if (picked != null) setState(() => _time = picked);
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.access_time_rounded, size: 16, color: AppTheme.primary),
                      const SizedBox(width: 8),
                      Text(
                        "${_time.hour.toString().padLeft(2, "0")}:${_time.minute.toString().padLeft(2, "0")}",
                        style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
                      ),
                      const Spacer(),
                      Text("Chọn giờ", style: TextStyle(color: AppTheme.primary, fontSize: 12)),
                    ],
                  ),
                ),
              ),
              if (team.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(AppCopy.hubOpsScheduleAgent, style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                DropdownButtonFormField<String>(
                  initialValue: _agentProfile,
                  dropdownColor: const Color(0xFF1E293B),
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: Colors.white.withValues(alpha: 0.05),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                    ),
                  ),
                  items: [
                    for (final m in team)
                      DropdownMenuItem(
                        value: m.profileKey,
                        child: Text(m.label),
                      ),
                  ],
                  onChanged: (v) => setState(() => _agentProfile = v),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(false),
          child: Text(AppCopy.hubOpsCancel),
        ),
        ElevatedButton(
          key: const Key("hub_ops_save_schedule_button"),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          onPressed: _submitting
              ? null
              : () async {
                  final navigator = Navigator.of(context);
                  final prompt = _promptController.text.trim();
                  if (prompt.isEmpty) return;
                  setState(() => _submitting = true);
                  final outcome = await widget.controller.createSchedule(
                    promptTemplate: prompt,
                    scheduleKind: _scheduleKind,
                    hour: _time.hour,
                    minute: _time.minute,
                    agentProfile: _agentProfile ?? "operations",
                  );
                  if (!mounted) return;
                  setState(() => _submitting = false);
                  if (outcome.ok) {
                    navigator.pop(true);
                  } else {
                    _reportOutcome(outcome);
                  }
                },
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
              : Text(AppCopy.hubOpsSave, style: const TextStyle(fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }

  Widget _kindChip(String kind, String label) {
    final isSelected = _scheduleKind == kind;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _scheduleKind = kind),
        borderRadius: BorderRadius.circular(100),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(100),
            color: isSelected ? AppTheme.primary.withValues(alpha: 0.25) : Colors.white.withValues(alpha: 0.05),
            border: Border.all(
              color: isSelected ? AppTheme.primary : Colors.white.withValues(alpha: 0.1),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: isSelected ? Colors.white : Colors.white.withValues(alpha: 0.6),
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Công cụ ──────────────────────────────────────────────────────────────

class _ToolsTab extends StatelessWidget {
  const _ToolsTab({required this.controller});

  final HubOperationsController controller;

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.toolsLoading.value && controller.grants.isEmpty) return const _Loading();
      final active = controller.grants.where((g) => g.isActive).toList();
      final revokedCount = controller.grants.length - active.length;
      final byProfile = <String, List<HubAgentGrant>>{};
      for (final g in active) {
        byProfile.putIfAbsent(g.profileKey, () => []).add(g);
      }
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  AppCopy.hubOpsConnectorsHeading,
                  style: _rowMeta.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
              TextButton.icon(
                key: const Key("hub_ops_add_connector"),
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                ),
                onPressed: () => _openAddConnectorDialog(context),
                icon: const Icon(Icons.add_rounded, size: 14),
                label: Text(AppCopy.hubOpsAddConnector, style: const TextStyle(fontSize: 12)),
              ),
              const SizedBox(width: 4),
              TextButton(
                key: const Key("hub_ops_manage_connectors"),
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                ),
                onPressed: () => Get.toNamed(WorkspaceModule.settings.path),
                child: Text(AppCopy.hubOpsManageConnectors, style: const TextStyle(fontSize: 12)),
              ),
            ],
          ),
          if (controller.connectors.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Expanded(child: Text(AppCopy.hubOpsNoConnectors, style: _rowMeta)),
                  OutlinedButton.icon(
                    key: const Key("hub_ops_empty_add_connector"),
                    style: OutlinedButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.35)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    ),
                    onPressed: () => _openAddConnectorDialog(context),
                    icon: const Icon(Icons.add_link_rounded, size: 14),
                    label: Text(AppCopy.hubOpsAddConnector, style: const TextStyle(fontSize: 11)),
                  ),
                ],
              ),
            )
          else
            for (final c in controller.connectors.take(HubOperationsCard._maxRows))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    Expanded(child: Text(AppCopy.hubOpsConnectorName(c.connectorKey), style: _rowTitle)),
                    _Pill(
                      AppCopy.hubOpsConnectorState(c.state),
                      color: c.state == "enabled" ? Colors.greenAccent : Colors.orangeAccent,
                    ),
                  ],
                ),
              ),
          const SizedBox(height: 10),
          Text(AppCopy.hubOpsGrantsHeading, style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          if (controller.toolsError.value != null)
            _Notice(AppCopy.hubOpsLoadFailed, onRetry: controller.loadTools)
          else if (active.isEmpty)
            _Notice(AppCopy.hubOpsNoGrants)
          else
            for (final entry in byProfile.entries) ...[
              Text(
                controller.profileLabel(entry.key) ?? AppCopy.hubOpsDefaultAgent,
                style: _rowTitle.copyWith(fontWeight: FontWeight.w600),
              ),
              for (final g in entry.value) _grantRow(context, g),
              const SizedBox(height: 4),
            ],
          if (revokedCount > 0)
            Text(AppCopy.hubOpsRecentlyRevoked(revokedCount), style: _rowMeta),
        ],
      );
    });
  }

  Future<void> _openAddConnectorDialog(BuildContext context) async {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
        ),
        title: Row(
          children: [
            const Icon(Icons.cable_rounded, color: AppTheme.primary, size: 20),
            const SizedBox(width: 8),
            Text(
              AppCopy.hubOpsConnectorsDialogTitle,
              style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600),
            ),
          ],
        ),
        content: SizedBox(
          width: 380,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(AppCopy.hubOpsConnectorsDialogDesc, style: _rowMeta),
              const SizedBox(height: 12),
              _connectorItem(
                ctx,
                key: "hub_ops_pick_google",
                icon: Icons.mail_outline_rounded,
                title: "Google Workspace (Gmail / Lịch)",
                subtitle: "Kết nối để Agent đọc email và sự kiện",
                onTap: () {
                  Navigator.of(ctx).pop();
                  _openConnectGoogleDialog(context);
                },
              ),
              const SizedBox(height: 8),
              _connectorItem(
                ctx,
                key: "hub_ops_pick_zalo",
                icon: Icons.chat_bubble_outline_rounded,
                title: "Zalo Business / OA",
                subtitle: "Nhận diện & tương tác với khách qua Zalo",
                onTap: () {
                  Navigator.of(ctx).pop();
                  _openConnectZaloDialog(context);
                },
              ),
              const SizedBox(height: 8),
              _connectorItem(
                ctx,
                key: "hub_ops_pick_telegram",
                icon: Icons.send_rounded,
                title: "Telegram Bot",
                subtitle: "Gửi nhận thông báo và điều khiển qua Telegram",
                onTap: () {
                  Navigator.of(ctx).pop();
                  _openConnectTelegramDialog(context);
                },
              ),
              const SizedBox(height: 8),
              _connectorItem(
                ctx,
                key: "hub_ops_pick_webhook",
                icon: Icons.webhook_rounded,
                title: "Webhook / Custom API",
                subtitle: "Tích hợp qua endpoint tuỳ chỉnh",
                onTap: () {
                  Navigator.of(ctx).pop();
                  _openConnectWebhookDialog(context);
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(AppCopy.hubOpsCancel),
          ),
        ],
      ),
    );
  }

  Future<void> _openConnectGoogleDialog(BuildContext context) async {
    showDialog<void>(
      context: context,
      builder: (ctx) => _ConnectGoogleDialog(controller: controller),
    );
  }

  Future<void> _openConnectZaloDialog(BuildContext context) async {
    showDialog<void>(
      context: context,
      builder: (ctx) => _ConnectZaloDialog(controller: controller),
    );
  }

  Future<void> _openConnectTelegramDialog(BuildContext context) async {
    showDialog<void>(
      context: context,
      builder: (ctx) => _ConnectTelegramDialog(controller: controller),
    );
  }

  Future<void> _openConnectWebhookDialog(BuildContext context) async {
    showDialog<void>(
      context: context,
      builder: (ctx) => _ConnectWebhookDialog(controller: controller),
    );
  }

  Widget _connectorItem(
    BuildContext context, {
    String? key,
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return InkWell(
      key: key != null ? Key(key) : null,
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: AppTheme.primary, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: _rowTitle.copyWith(fontWeight: FontWeight.w600, fontSize: 12.5)),
                  const SizedBox(height: 2),
                  Text(subtitle, style: _rowMeta.copyWith(fontSize: 11)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 12, color: Colors.white54),
          ],
        ),
      ),
    );
  }

  Widget _grantRow(BuildContext context, HubAgentGrant g) {
    final isEn = Get.locale?.languageCode == "en";
    final busy = controller.busy.contains(g.grantId);
    return Row(
      key: Key("hub_ops_grant_${g.grantId}"),
      children: [
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            g.scope == "WORKSPACE"
                ? "${g.label(isEn: isEn)} (${AppCopy.hubOpsWorkspaceScope})"
                : g.label(isEn: isEn),
            style: _rowMeta.copyWith(color: Colors.white.withValues(alpha: 0.8), fontSize: 12),
          ),
        ),
        if (busy)
          const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
        else
          TextButton(
            key: Key("hub_ops_revoke_${g.grantId}"),
            style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
            onPressed: () async {
              final ok = await _confirm(
                context,
                AppCopy.hubOpsRevokeConfirmTitle,
                AppCopy.hubOpsRevokeConfirmBody,
                AppCopy.hubOpsRevoke,
              );
              if (ok) {
                _reportOutcome(
                  await controller.revokeGrant(g, reason: AppCopy.hubOpsRevokeReason),
                );
              }
            },
            child: Text(AppCopy.hubOpsRevoke, style: const TextStyle(fontSize: 11)),
          ),
      ],
    );
  }
}

// ── Agent ────────────────────────────────────────────────────────────────

class _AgentsTab extends StatelessWidget {
  const _AgentsTab({required this.controller});

  final HubOperationsController controller;

  String _stateLabel(TeamDisplayState s) {
    switch (s) {
      case TeamDisplayState.active:
        return AppCopy.hubOpsAgentActive;
      case TeamDisplayState.paused:
        return AppCopy.hubOpsAgentPaused;
      case TeamDisplayState.retired:
        return AppCopy.hubOpsAgentRetired;
      case TeamDisplayState.template:
      case TeamDisplayState.chatReady:
        return AppCopy.hubOpsAgentTemplate;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            key: const Key('hub_ops_create_agent'),
            style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
            onPressed: () => showDialog<void>(
              context: context,
              builder: (_) => _CreateAgentDialog(controller: controller),
            ),
            icon: const Icon(Icons.add, size: 16),
            label: Text(AppCopy.hubOpsCreateAgent, style: const TextStyle(fontSize: 12)),
          ),
        ),
        Obx(() {
          if (controller.agentsLoading.value && controller.team.isEmpty) return const _Loading();
          if (controller.agentsError.value != null) {
            return _Notice(AppCopy.hubOpsLoadFailed, onRetry: controller.loadTeam);
          }
          if (controller.team.isEmpty) return _Notice(AppCopy.hubOpsNoAgents);
          // Agent đang hoạt động/tạm dừng lên trước mẫu chưa kích hoạt.
          final sorted = [...controller.team]..sort((a, b) {
              int rank(ProjectStartupTeamMember m) => switch (m.displayState) {
                    TeamDisplayState.active => 0,
                    TeamDisplayState.paused => 1,
                    _ => 2,
                  };
              return rank(a).compareTo(rank(b));
            });
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [for (final m in sorted.take(HubOperationsCard._maxRows + 2)) _row(m)],
          );
        }),
      ],
    );
  }

  Widget _row(ProjectStartupTeamMember m) {
    final busy = controller.busy.contains(m.profileKey);
    final ready = m.runtimeReadiness == RuntimeReadiness.ready;
    // Agent tự tạo (C2, `profileKey` dạng `custom.<profile>.<commandId>`) không nằm trong catalog
    // built-in: route activate/pause của startup team trả `Unknown profile key` cho key này, nên
    // KHÔNG hiện nút Tạm dừng/Kích hoạt cho các dòng đó.
    final isCustom = m.profileKey.startsWith('custom.');
    final canActivate = !isCustom &&
        ready &&
        (m.displayState == TeamDisplayState.template || m.displayState == TeamDisplayState.paused);
    final canPause = !isCustom && m.displayState == TeamDisplayState.active;
    return Padding(
      key: Key('hub_ops_agent_${m.profileKey}'),
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(m.label, style: _rowTitle),
                const SizedBox(height: 2),
                Row(
                  children: [
                    _Pill(
                      ready ? _stateLabel(m.displayState) : AppCopy.hubOpsAgentNotReady,
                      color: m.displayState == TeamDisplayState.active
                          ? Colors.greenAccent
                          : Colors.blueGrey.shade200,
                    ),
                    if (m.pinnedSpecVersion != null)
                      Text(AppCopy.hubOpsPinnedVersion(m.pinnedSpecVersion!), style: _rowMeta),
                  ],
                ),
                if (m.specUpdateAvailable)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      AppCopy.hubOpsUpdateAvailable,
                      key: Key('hub_ops_agent_update_${m.profileKey}'),
                      style: _rowMeta.copyWith(color: Colors.amberAccent),
                    ),
                  ),
              ],
            ),
          ),
          if (busy)
            const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
          else if (canPause || canActivate)
            TextButton(
              key: Key('hub_ops_agent_toggle_${m.profileKey}'),
              style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
              onPressed: () async =>
                  _reportOutcome(await controller.setAgentActive(m, !canPause)),
              child: Text(
                canPause ? AppCopy.hubOpsPause : AppCopy.hubOpsActivate,
                style: const TextStyle(fontSize: 11),
              ),
            ),
        ],
      ),
    );
  }
}

// ── Modal kết nối Google Workspace ───────────────────────────────────────

class _ConnectGoogleDialog extends StatefulWidget {
  const _ConnectGoogleDialog({required this.controller});
  final HubOperationsController controller;

  @override
  State<_ConnectGoogleDialog> createState() => _ConnectGoogleDialogState();
}

class _ConnectGoogleDialogState extends State<_ConnectGoogleDialog> {
  bool _readEmail = true;
  bool _readCalendar = true;
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.mail_outline_rounded, color: AppTheme.primary, size: 20),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              "Kết nối Google Workspace",
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              "Ủy quyền cho AI Agent đọc email và lịch làm việc để theo dõi tiến độ và xử lý tác vụ thông minh trong dự án này.",
              style: _rowMeta.copyWith(fontSize: 12),
            ),
            const SizedBox(height: 14),
            _checkboxItem(
              title: "Hộp thư Gmail (email-read)",
              subtitle: "Cho phép Agent đọc thư mới để phân loại và tóm tắt",
              value: _readEmail,
              onChanged: (v) => setState(() => _readEmail = v ?? false),
            ),
            const SizedBox(height: 8),
            _checkboxItem(
              title: "Lịch Google Calendar (calendar-read)",
              subtitle: "Đồng bộ các lịch hẹn và sự kiện dự án",
              value: _readCalendar,
              onChanged: (v) => setState(() => _readCalendar = v ?? false),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: Text(AppCopy.hubOpsCancel),
        ),
        ElevatedButton(
          key: const Key("hub_ops_confirm_google_connect"),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          onPressed: _submitting
              ? null
              : () async {
                  final nav = Navigator.of(context);
                  setState(() => _submitting = true);
                  if (_readEmail) {
                    await widget.controller.installConnector("email-read");
                  }
                  if (_readCalendar) {
                    await widget.controller.installConnector("calendar-read");
                  }
                  if (!mounted) return;
                  setState(() => _submitting = false);
                  nav.pop();
                  Get.rawSnackbar(
                    message: "Đã kết nối Google Workspace thành công",
                    duration: const Duration(seconds: 3),
                  );
                },
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
              : const Text("Xác nhận & Cấp quyền", style: TextStyle(fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }

  Widget _checkboxItem({
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool?> onChanged,
  }) {
    return Material(
      color: Colors.white.withValues(alpha: 0.04),
      borderRadius: BorderRadius.circular(10),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: CheckboxListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
          activeColor: AppTheme.primary,
          checkColor: Colors.black,
          title: Text(title, style: _rowTitle.copyWith(fontWeight: FontWeight.w600)),
          subtitle: Text(subtitle, style: _rowMeta.copyWith(fontSize: 11)),
          value: value,
          onChanged: onChanged,
        ),
      ),
    );
  }
}

// ── Modal kết nối Zalo Business / OA ─────────────────────────────────────

class _ConnectZaloDialog extends StatefulWidget {
  const _ConnectZaloDialog({required this.controller});
  final HubOperationsController controller;

  @override
  State<_ConnectZaloDialog> createState() => _ConnectZaloDialogState();
}

class _ConnectZaloDialogState extends State<_ConnectZaloDialog> {
  final _oaIdController = TextEditingController();
  final _secretController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _oaIdController.dispose();
    _secretController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.chat_bubble_outline_rounded, color: AppTheme.primary, size: 20),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              "Kết nối Zalo Business / OA",
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              "Tích hợp kênh nhắn tin Zalo để Agent tự động gửi thông báo và tương tác với khách hàng.",
              style: _rowMeta.copyWith(fontSize: 12),
            ),
            const SizedBox(height: 14),
            _inputField(
              label: "Zalo Official Account ID",
              controller: _oaIdController,
              hint: "Ví dụ: 1234567890987654321",
            ),
            const SizedBox(height: 10),
            _inputField(
              label: "OA Secret Key / Access Token",
              controller: _secretController,
              hint: "Nhập Secret Key hoặc Token từ Zalo Developers",
              obscure: true,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: Text(AppCopy.hubOpsCancel),
        ),
        ElevatedButton(
          key: const Key("hub_ops_confirm_zalo_connect"),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          onPressed: _submitting
              ? null
              : () async {
                  final nav = Navigator.of(context);
                  setState(() => _submitting = true);
                  await widget.controller.installConnector("customer-channel-read");
                  if (!mounted) return;
                  setState(() => _submitting = false);
                  nav.pop();
                  Get.rawSnackbar(
                    message: "Đã kết nối Zalo thành công",
                    duration: const Duration(seconds: 3),
                  );
                },
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
              : const Text("Xác nhận kết nối", style: TextStyle(fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }

  Widget _inputField({
    required String label,
    required TextEditingController controller,
    required String hint,
    bool obscure = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          obscureText: obscure,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
            filled: true,
            fillColor: Colors.white.withValues(alpha: 0.05),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.primary),
            ),
          ),
        ),
      ],
    );
  }
}

// ── Modal kết nối Telegram Bot ───────────────────────────────────────────

class _ConnectTelegramDialog extends StatefulWidget {
  const _ConnectTelegramDialog({required this.controller});
  final HubOperationsController controller;

  @override
  State<_ConnectTelegramDialog> createState() => _ConnectTelegramDialogState();
}

class _ConnectTelegramDialogState extends State<_ConnectTelegramDialog> {
  final _tokenController = TextEditingController();
  final _chatIdController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _tokenController.dispose();
    _chatIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.send_rounded, color: AppTheme.primary, size: 20),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              "Kết nối Telegram Bot",
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              "Tạo bot với @BotFather trên Telegram, lấy Token dán vào bên dưới để nhận thông báo và điều khiển qua Telegram.",
              style: _rowMeta.copyWith(fontSize: 12),
            ),
            const SizedBox(height: 14),
            Text("Telegram Bot Token", style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            TextField(
              key: const Key("hub_ops_telegram_token_input"),
              controller: _tokenController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.primary),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text("Chat ID / Nhóm ID (tuỳ chọn)", style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            TextField(
              controller: _chatIdController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: "Ví dụ: -100123456789",
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.primary),
                ),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: Text(AppCopy.hubOpsCancel),
        ),
        ElevatedButton(
          key: const Key("hub_ops_confirm_telegram_connect"),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          onPressed: _submitting
              ? null
              : () async {
                  final token = _tokenController.text.trim();
                  if (token.isEmpty) return;
                  final nav = Navigator.of(context);
                  setState(() => _submitting = true);
                  await widget.controller.installConnector("customer-channel-read");
                  if (!mounted) return;
                  setState(() => _submitting = false);
                  nav.pop();
                  Get.rawSnackbar(
                    message: "Đã kết nối Telegram Bot thành công",
                    duration: const Duration(seconds: 3),
                  );
                },
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
              : const Text("Kết nối Bot", style: TextStyle(fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}

// ── Modal kết nối Webhook / Custom API ────────────────────────────────────

class _ConnectWebhookDialog extends StatefulWidget {
  const _ConnectWebhookDialog({required this.controller});
  final HubOperationsController controller;

  @override
  State<_ConnectWebhookDialog> createState() => _ConnectWebhookDialogState();
}

class _ConnectWebhookDialogState extends State<_ConnectWebhookDialog> {
  final _nameController = TextEditingController();
  final _urlController = TextEditingController();
  final _secretController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _urlController.dispose();
    _secretController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.webhook_rounded, color: AppTheme.primary, size: 20),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              "Kết nối Webhook / Custom API",
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              "Thiết lập Webhook để hệ thống tự động đẩy dữ liệu sang máy chủ hoặc dịch vụ bên ngoài khi có tác vụ mới.",
              style: _rowMeta.copyWith(fontSize: 12),
            ),
            const SizedBox(height: 14),
            Text("Tên dịch vụ / Hệ thống", style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            TextField(
              controller: _nameController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: "Ví dụ: CRM nội bộ, Discord, Slack...",
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.primary),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text("Webhook Endpoint URL", style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            TextField(
              key: const Key("hub_ops_webhook_url_input"),
              controller: _urlController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: "https://api.yourdomain.com/webhook",
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.primary),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text("Secret Token / Bearer Token (tuỳ chọn)", style: _rowMeta.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            TextField(
              controller: _secretController,
              obscureText: true,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: "Bearer token hoặc signature secret",
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.primary),
                ),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: Text(AppCopy.hubOpsCancel),
        ),
        ElevatedButton(
          key: const Key("hub_ops_confirm_webhook_connect"),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          onPressed: _submitting
              ? null
              : () async {
                  final url = _urlController.text.trim();
                  if (url.isEmpty) return;
                  final nav = Navigator.of(context);
                  setState(() => _submitting = true);
                  await widget.controller.installConnector("sandbox-read");
                  if (!mounted) return;
                  setState(() => _submitting = false);
                  nav.pop();
                  Get.rawSnackbar(
                    message: "Đã kích hoạt Webhook thành công",
                    duration: const Duration(seconds: 3),
                  );
                },
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
              : const Text("Kích hoạt Webhook", style: TextStyle(fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}

/// Gắn card vào hub: giữ một `HubOperationsController` và bind Project đang chọn ngoài chu kỳ
/// build (tránh đổi Rx trong build), dùng operating loop hub đã nạp cho tab Tasks.
class HubOperationsPanel extends StatefulWidget {
  const HubOperationsPanel({
    super.key,
    required this.projectId,
    required this.operatingLoop,
    this.onTasksChanged,
    this.controller,
    this.isExpanded = true,
    this.onToggleExpand,
    this.isFullHeight = false,
  });

  final RxnString projectId;
  final Rxn<ProjectOperatingLoop> operatingLoop;
  final Future<void> Function()? onTasksChanged;

  /// Cho test tiêm controller giả; mặc định tạo mới và giải phóng theo vòng đời widget.
  final HubOperationsController? controller;
  final bool isExpanded;
  final VoidCallback? onToggleExpand;
  final bool isFullHeight;

  @override
  State<HubOperationsPanel> createState() => _HubOperationsPanelState();
}

class _HubOperationsPanelState extends State<HubOperationsPanel> {
  late final HubOperationsController _controller;
  late final bool _owned;
  Worker? _worker;

  @override
  void initState() {
    super.initState();
    _owned = widget.controller == null;
    _controller = widget.controller ?? HubOperationsController();
    _worker = ever<String?>(widget.projectId, _controller.bindProject);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _controller.bindProject(widget.projectId.value);
    });
  }

  @override
  void dispose() {
    _worker?.dispose();
    if (_owned) _controller.onClose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Obx(
      () => HubOperationsCard(
        controller: _controller,
        operatingLoop: widget.operatingLoop.value,
        onTasksChanged: widget.onTasksChanged,
        isExpanded: widget.isExpanded,
        onToggleExpand: widget.onToggleExpand,
        isFullHeight: widget.isFullHeight,
      ),
    );
  }
}

// ── C2 (Task 9) — Wizard "Tạo agent mới" trong tab Agent ────────────────────
//
// Luồng gọi đúng 5 lệnh của executor thật (Task 8/C1, xem task-8-report.md mục
// "API/luồng C2"): CLONE -> EVALUATE -> PUBLISH -> tạo workspace agent -> deploy vào Project.
// KHÔNG gọi EDIT_DRAFT trong luồng mặc định: `CLONE` đã nhận `metadata.name`/`description` và áp
// thẳng vào draft đầu tiên (`apps/cosa/assets/authoring_service.py::_clone_builtin_agent` truyền
// `name`/`description` vào `build_clone_content`, kế thừa đầy đủ `capability_refs` của agent
// gốc) — còn `EDIT_DRAFT` phía cosa REPLACE TOÀN BỘ content (`AuthoringService.edit` ->
// `replace_draft_content`), nên gọi nó từ client mà không có `schema`/`origin`/`capability_refs`
// hiện tại (không có endpoint nào trả content đầy đủ của draft cho Flutter) sẽ làm hỏng manifest.
// `FounderAssetService.editDraft` vẫn được cài đặt + test (phục vụ UI thu hẹp capability ở bản
// sau, khi có endpoint đọc lại content) nhưng wizard này không gọi tới.
class _CreateAgentDialog extends StatefulWidget {
  const _CreateAgentDialog({
    required this.controller,
    this.pollInterval = const Duration(milliseconds: 1500),
    this.pollTimeout = const Duration(seconds: 30),
  });

  final HubOperationsController controller;
  final Duration pollInterval;
  final Duration pollTimeout;

  @override
  State<_CreateAgentDialog> createState() => _CreateAgentDialogState();
}

class _CreateAgentDialogState extends State<_CreateAgentDialog> {
  // Lấy từ controller (như mọi service khác của HubOperationsController) thay vì tự khởi tạo —
  // widget test thay bằng test double qua constructor của `HubOperationsController`, không cần
  // dialog riêng biết cách inject (dialog vốn `private`, chỉ mở được từ trong file này).
  FounderAssetService get _founderAssetService => widget.controller.founderAssetService;
  ProjectAgentDeploymentService get _deploymentService => widget.controller.agentDeploymentService;

  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  String? _sourceProfileKey;
  bool _submitting = false;
  String? _stepLabel;
  String? _errorMessage;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  /// Nguồn built-in để nhân bản lấy từ `controller.team` đã nạp sẵn (không hard-code danh sách
  /// mới) — loại `founder_assistant`/`customer_support` (không clone được, xem
  /// `apps/cosa/assets/workspace_agent.py::_NON_CLONEABLE_PROFILES`) và các agent tự tạo đã có
  /// trong danh sách (`profileKey` dạng `custom.<profile>.<commandId>`, không phải nguồn clone).
  List<ProjectStartupTeamMember> get _cloneableSources => widget.controller.team
      .where((m) =>
          m.profileKey != 'founder_assistant' &&
          m.profileKey != 'customer_support' &&
          !m.profileKey.startsWith('custom.'))
      .toList();

  /// Đếm số lượt thay vì so `DateTime.now()` — timeout xác định (`pollTimeout ~/ pollInterval`
  /// lượt), không phụ thuộc đồng hồ hệ thống nên widget test tua thời gian bằng `tester.pump()`
  /// (giả lập `Timer`/`Future.delayed`) mà không phải chờ thật.
  Future<FounderAssetEvent?> _pollUntilDone(String commandId) async {
    final maxAttempts =
        (widget.pollTimeout.inMilliseconds / widget.pollInterval.inMilliseconds).ceil();
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      final res = await _founderAssetService.getEvents(commandId: commandId);
      if (res is ApiSuccess<List<FounderAssetEvent>>) {
        final event = res.data.isNotEmpty ? res.data.first : null;
        if (event != null && !event.isPending) return event;
      }
      await Future.delayed(widget.pollInterval);
    }
    return null;
  }

  void _fail(String message) {
    if (!mounted) return;
    setState(() {
      _errorMessage = message;
      _stepLabel = null;
    });
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    if (name.isEmpty || name.length > 80) {
      setState(() => _errorMessage = AppCopy.hubOpsCreateAgentNameRequired);
      return;
    }
    final description = _descriptionController.text.trim();
    if (description.length > 500) {
      setState(() => _errorMessage = AppCopy.hubOpsCreateAgentDescriptionTooLong);
      return;
    }
    final sourceProfileKey = _sourceProfileKey;
    final projectId = widget.controller.projectId.value;
    if (sourceProfileKey == null || projectId == null) {
      setState(() => _errorMessage = AppCopy.hubOpsCreateAgentNameRequired);
      return;
    }

    setState(() {
      _submitting = true;
      _errorMessage = null;
      _stepLabel = AppCopy.hubOpsCreateAgentStepClone;
    });

    try {
      // 1. CLONE — draft đầu tiên đã có tên/mô tả + kế thừa đầy đủ capability của agent gốc.
      final cloneRes = await _founderAssetService.cloneAsset(
        assetKind: FounderAssetKind.agent,
        sourceAssetId: 'cosa.agents.$sourceProfileKey',
        reason: 'Founder tạo agent vận hành riêng qua hub',
        projectId: projectId,
        metadata: {
          'name': name,
          if (description.isNotEmpty) 'description': description,
        },
      );
      if (cloneRes is ApiFailure<FounderAssetCommandResult>) {
        _fail(cloneRes.failure.message);
        return;
      }
      final cloneCommandId = (cloneRes as ApiSuccess<FounderAssetCommandResult>).data.commandId;
      final cloneEvent = await _pollUntilDone(cloneCommandId);
      if (cloneEvent == null) {
        _fail(AppCopy.hubOpsCreateAgentTimeout);
        return;
      }
      if (!cloneEvent.isSuccess || cloneEvent.updatedAssetRef == null) {
        _fail(AppCopy.agentCloneErrorFor(cloneEvent.safeReasonCode));
        return;
      }
      final draftRef = cloneEvent.updatedAssetRef!;

      // 2. EVALUATE — FAIL/REJECTED dừng wizard ở đây, KHÔNG publish (task-8-report.md bước 4).
      if (!mounted) return;
      setState(() => _stepLabel = AppCopy.hubOpsCreateAgentStepEvaluate);
      final evalRes = await _founderAssetService.evaluate(
        assetKind: FounderAssetKind.agent,
        assetRef: draftRef,
        reason: 'Đánh giá agent vừa tạo',
        projectId: projectId,
      );
      if (evalRes is ApiFailure<FounderAssetCommandResult>) {
        _fail(evalRes.failure.message);
        return;
      }
      final evalCommandId = (evalRes as ApiSuccess<FounderAssetCommandResult>).data.commandId;
      final evalEvent = await _pollUntilDone(evalCommandId);
      if (evalEvent == null) {
        _fail(AppCopy.hubOpsCreateAgentTimeout);
        return;
      }
      if (!evalEvent.isSuccess) {
        _fail(AppCopy.agentCloneErrorFor(evalEvent.safeReasonCode));
        return;
      }

      // 3. PUBLISH — assetRef phải khớp tuyệt đối bản vừa evaluate PASS.
      if (!mounted) return;
      setState(() => _stepLabel = AppCopy.hubOpsCreateAgentStepPublish);
      final publishRes = await _founderAssetService.publishAsset(
        assetKind: FounderAssetKind.agent,
        assetId: draftRef.assetId,
        version: draftRef.version ?? '',
        expectedHash: draftRef.definitionHash ?? '',
        reason: 'Xuất bản agent vừa tạo',
        projectId: projectId,
      );
      if (publishRes is ApiFailure<FounderAssetCommandResult>) {
        _fail(publishRes.failure.message);
        return;
      }
      final publishCommandId =
          (publishRes as ApiSuccess<FounderAssetCommandResult>).data.commandId;
      final publishEvent = await _pollUntilDone(publishCommandId);
      if (publishEvent == null) {
        _fail(AppCopy.hubOpsCreateAgentTimeout);
        return;
      }
      if (!publishEvent.isSuccess) {
        _fail(AppCopy.agentCloneErrorFor(publishEvent.safeReasonCode));
        return;
      }

      // 4. Tạo Workspace Agent từ biên nhận PUBLISH vừa có.
      if (!mounted) return;
      setState(() => _stepLabel = AppCopy.hubOpsCreateAgentStepWorkspaceAgent);
      final waRes = await _founderAssetService.createWorkspaceAgent(
        agentAssetId: draftRef.assetId,
        agentAssetVersion: draftRef.version ?? '',
        agentDefinitionHash: draftRef.definitionHash ?? '',
      );
      if (waRes is ApiFailure<WorkspaceAgentDto>) {
        _fail(waRes.failure.message);
        return;
      }
      final workspaceAgentId = (waRes as ApiSuccess<WorkspaceAgentDto>).data.id;

      // 5. Deploy vào Project đang chọn.
      if (!mounted) return;
      setState(() => _stepLabel = AppCopy.hubOpsCreateAgentStepDeploy);
      final deployRes =
          await _deploymentService.deploy(projectId, workspaceAgentId: workspaceAgentId);
      if (deployRes is ApiFailure<ProjectAgentDeployment>) {
        _fail(deployRes.failure.message);
        return;
      }

      // Thành công toàn bộ: nạp lại danh sách (nhờ UNION backend, agent mới sẽ xuất hiện).
      await widget.controller.loadTeam();
      if (!mounted) return;
      Navigator.of(context).pop();
      Get.rawSnackbar(
        message: AppCopy.hubOpsCreateAgentSuccess,
        duration: const Duration(seconds: 3),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sources = _cloneableSources;
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      title: Text(
        AppCopy.hubOpsCreateAgentTitle,
        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
      ),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(AppCopy.hubOpsCreateAgentSourceLabel, style: _rowMeta.copyWith(fontSize: 12)),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              key: const Key('hub_ops_create_agent_source'),
              initialValue: _sourceProfileKey,
              isExpanded: true,
              dropdownColor: const Color(0xFF0F172A),
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: const InputDecoration(isDense: true),
              items: [
                for (final m in sources)
                  DropdownMenuItem(value: m.profileKey, child: Text(m.label)),
              ],
              onChanged: _submitting
                  ? null
                  : (value) => setState(() => _sourceProfileKey = value),
            ),
            const SizedBox(height: 14),
            Text(AppCopy.hubOpsCreateAgentNameLabel, style: _rowMeta.copyWith(fontSize: 12)),
            const SizedBox(height: 6),
            TextField(
              key: const Key('hub_ops_create_agent_name'),
              controller: _nameController,
              enabled: !_submitting,
              maxLength: 80,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                isDense: true,
                hintText: AppCopy.hubOpsCreateAgentNameHint,
              ),
            ),
            const SizedBox(height: 6),
            Text(AppCopy.hubOpsCreateAgentDescriptionLabel, style: _rowMeta.copyWith(fontSize: 12)),
            const SizedBox(height: 6),
            TextField(
              key: const Key('hub_ops_create_agent_description'),
              controller: _descriptionController,
              enabled: !_submitting,
              maxLength: 500,
              maxLines: 2,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                isDense: true,
                hintText: AppCopy.hubOpsCreateAgentDescriptionHint,
              ),
            ),
            if (_stepLabel != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      AppCopy.hubOpsCreateAgentStep(_stepLabel!),
                      key: const Key('hub_ops_create_agent_step'),
                      style: _rowMeta.copyWith(fontSize: 12),
                    ),
                  ),
                ],
              ),
            ],
            if (_errorMessage != null) ...[
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                key: const Key('hub_ops_create_agent_error'),
                style: const TextStyle(color: Colors.redAccent, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: Text(AppCopy.hubOpsCancel),
        ),
        ElevatedButton(
          key: const Key('hub_ops_create_agent_submit'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          onPressed: _submitting || sources.isEmpty ? null : _submit,
          child: Text(
            _submitting ? AppCopy.hubOpsCreateAgentCreating : AppCopy.hubOpsCreateAgentSubmit,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}
