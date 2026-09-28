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
  });

  final HubOperationsController controller;

  /// Operating loop do controller hub nạp sẵn (nguồn cho tab Tasks).
  final ProjectOperatingLoop? operatingLoop;
  final Future<void> Function()? onTasksChanged;

  static const _maxRows = 6;

  @override
  Widget build(BuildContext context) {
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
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              AppCopy.hubOpsTitle,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 8),
            _TabStrip(current: current, onSelect: controller.selectTab),
            const SizedBox(height: 10),
            switch (current) {
              HubOperationsTab.tasks => _TasksTab(
                  controller: controller,
                  operatingLoop: operatingLoop,
                  onTasksChanged: onTasksChanged,
                ),
              HubOperationsTab.schedules => _SchedulesTab(controller: controller),
              HubOperationsTab.tools => _ToolsTab(controller: controller),
              HubOperationsTab.agents => _AgentsTab(controller: controller),
            },
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
    return Row(
      children: [
        for (final entry in labels.entries)
          Expanded(
            child: InkWell(
              key: Key('hub_ops_tab_${entry.key.name}'),
              borderRadius: BorderRadius.circular(8),
              onTap: () => onSelect(entry.key),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 6),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: entry.key == current
                      ? AppTheme.primary.withValues(alpha: 0.22)
                      : Colors.transparent,
                ),
                child: Text(
                  entry.value,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    color: entry.key == current
                        ? Colors.white
                        : Colors.white.withValues(alpha: 0.6),
                    fontWeight: entry.key == current ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
            ),
          ),
      ],
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
    final hh = (s.hour ?? 0).toString().padLeft(2, '0');
    final mm = (s.minute ?? 0).toString().padLeft(2, '0');
    final time = '$hh:$mm';
    switch (s.scheduleKind) {
      case 'daily':
        return AppCopy.hubOpsDaily(time);
      case 'weekdays':
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
      if (controller.schedules.isEmpty) return _Notice(AppCopy.hubOpsNoSchedules);
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final s in controller.schedules.take(HubOperationsCard._maxRows)) _row(context, s),
        ],
      );
    });
  }

  Widget _row(BuildContext context, HubSchedule s) {
    final busy = controller.busy.contains(s.id);
    final last = controller.lastExecutions[s.id];
    final agent = controller.profileLabel(s.agentProfile) ?? AppCopy.hubOpsDefaultAgent;
    return Padding(
      key: Key('hub_ops_schedule_${s.id}'),
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
          Text('${_cadence(s)} · $agent', style: _rowMeta),
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
                  key: 'run_${s.id}',
                  icon: Icons.play_arrow_rounded,
                  label: AppCopy.hubOpsRunNow,
                  onTap: s.isEnabled
                      ? () async => _reportOutcome(await controller.runScheduleNow(s.id))
                      : null,
                ),
                _action(
                  key: 'toggle_${s.id}',
                  icon: s.isEnabled ? Icons.pause_rounded : Icons.play_circle_outline,
                  label: s.isEnabled ? AppCopy.hubOpsPause : AppCopy.hubOpsResume,
                  onTap: () async => _reportOutcome(
                    await controller.setScheduleState(s.id, s.isEnabled ? 'paused' : 'enabled'),
                  ),
                ),
                _action(
                  key: 'archive_${s.id}',
                  icon: Icons.archive_outlined,
                  label: AppCopy.hubOpsArchive,
                  onTap: () async {
                    final ok = await _confirm(
                      context,
                      AppCopy.hubOpsArchiveConfirmTitle,
                      AppCopy.hubOpsArchiveConfirmBody,
                      AppCopy.hubOpsArchive,
                    );
                    if (ok) _reportOutcome(await controller.setScheduleState(s.id, 'archived'));
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
      key: Key('hub_ops_schedule_$key'),
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
              TextButton(
                key: const Key('hub_ops_manage_connectors'),
                style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
                onPressed: () => Get.toNamed(WorkspaceModule.settings.path),
                child: Text(AppCopy.hubOpsManageConnectors, style: const TextStyle(fontSize: 12)),
              ),
            ],
          ),
          if (controller.connectors.isEmpty)
            Text(AppCopy.hubOpsNoConnectors, style: _rowMeta)
          else
            for (final c in controller.connectors.take(HubOperationsCard._maxRows))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    Expanded(child: Text(AppCopy.hubOpsConnectorName(c.connectorKey), style: _rowTitle)),
                    _Pill(
                      AppCopy.hubOpsConnectorState(c.state),
                      color: c.state == 'enabled' ? Colors.greenAccent : Colors.orangeAccent,
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

  Widget _grantRow(BuildContext context, HubAgentGrant g) {
    final isEn = Get.locale?.languageCode == 'en';
    final busy = controller.busy.contains(g.grantId);
    return Row(
      key: Key('hub_ops_grant_${g.grantId}'),
      children: [
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            g.scope == 'WORKSPACE'
                ? '${g.label(isEn: isEn)} (${AppCopy.hubOpsWorkspaceScope})'
                : g.label(isEn: isEn),
            style: _rowMeta.copyWith(color: Colors.white.withValues(alpha: 0.8), fontSize: 12),
          ),
        ),
        if (busy)
          const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
        else
          TextButton(
            key: Key('hub_ops_revoke_${g.grantId}'),
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

/// Gắn card vào hub: giữ một `HubOperationsController` và bind Project đang chọn ngoài chu kỳ
/// build (tránh đổi Rx trong build), dùng operating loop hub đã nạp cho tab Tasks.
class HubOperationsPanel extends StatefulWidget {
  const HubOperationsPanel({
    super.key,
    required this.projectId,
    required this.operatingLoop,
    this.onTasksChanged,
    this.controller,
  });

  final RxnString projectId;
  final Rxn<ProjectOperatingLoop> operatingLoop;
  final Future<void> Function()? onTasksChanged;

  /// Cho test tiêm controller giả; mặc định tạo mới và giải phóng theo vòng đời widget.
  final HubOperationsController? controller;

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
