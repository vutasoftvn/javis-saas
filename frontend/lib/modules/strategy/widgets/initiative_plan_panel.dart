import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../models/strategy_workflow_models.dart';
import '../services/strategy_workflow_service.dart';

class InitiativeTaskItem {
  final String id;
  final String title;
  final String? initiativeId;
  final bool isBau;

  const InitiativeTaskItem({
    required this.id,
    required this.title,
    this.initiativeId,
    this.isBau = false,
  });
}

class InitiativePlanPanel extends StatefulWidget {
  final String? strategicObjectiveId;
  final String? sourceTowsOptionId;
  final String? cycleId;
  final List<String> availableKrIds;
  final StrategyWorkflowService? workflowService;
  final void Function(InitiativeModel initiative)? onInitiativeApproved;

  const InitiativePlanPanel({
    super.key,
    this.strategicObjectiveId,
    this.sourceTowsOptionId,
    this.cycleId,
    this.availableKrIds = const [],
    this.workflowService,
    this.onInitiativeApproved,
  });

  @override
  State<InitiativePlanPanel> createState() => _InitiativePlanPanelState();
}

class _InitiativePlanPanelState extends State<InitiativePlanPanel> {
  late final StrategyWorkflowService _service;
  List<InitiativeModel> _initiatives = [];
  final List<InitiativeTaskItem> _tasks = [];
  bool _isLoading = false;
  String? _errorMessage;
  bool _showCreateDialog = false;

  // New initiative form controllers
  final _titleController = TextEditingController();
  final _outcomeController = TextEditingController();
  final _ownerController = TextEditingController();
  final _targetDateController = TextEditingController();
  final _milestoneController = TextEditingController();
  final Set<String> _selectedKrs = {};

  // Task creation controllers
  final _taskTitleController = TextEditingController();
  String? _selectedTaskInitiativeId;
  bool _isBauTask = false;
  String? _taskError;

  @override
  void initState() {
    super.initState();
    _service = widget.workflowService ?? StrategyWorkflowService();
    _loadInitiatives();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _outcomeController.dispose();
    _ownerController.dispose();
    _targetDateController.dispose();
    _milestoneController.dispose();
    _taskTitleController.dispose();
    super.dispose();
  }

  Future<void> _loadInitiatives() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final items = await _service.listInitiatives(
        strategicObjectiveId: widget.strategicObjectiveId,
      );
      if (mounted) {
        setState(() {
          _initiatives = items;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _createInitiativeDraft() async {
    final title = _titleController.text.trim();
    if (title.isEmpty) return;

    setState(() => _isLoading = true);
    try {
      final milestones = _milestoneController.text.trim().isNotEmpty
          ? [
              {'title': _milestoneController.text.trim()},
            ]
          : <dynamic>[];

      final created = await _service.createInitiative(
        title: title,
        strategicObjectiveId: widget.strategicObjectiveId,
        sourceTowsOptionId: widget.sourceTowsOptionId,
        intendedOutcome: _outcomeController.text.trim().isNotEmpty
            ? _outcomeController.text.trim()
            : null,
        targetDate: _targetDateController.text.trim().isNotEmpty
            ? _targetDateController.text.trim()
            : null,
        milestones: milestones,
        ownerMemberId: _ownerController.text.trim().isNotEmpty
            ? _ownerController.text.trim()
            : null,
        keyResultIds: _selectedKrs.toList(),
      );

      setState(() {
        _initiatives = [created, ..._initiatives];
        _showCreateDialog = false;
        _isLoading = false;
        _titleController.clear();
        _outcomeController.clear();
        _ownerController.clear();
        _targetDateController.clear();
        _milestoneController.clear();
        _selectedKrs.clear();
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _approveInitiative(InitiativeModel init) async {
    setState(() => _isLoading = true);
    try {
      final approved = await _service.approveInitiative(
        init.id,
        reason: 'Chấp thuận kế hoạch thực thi chiến lược',
      );
      setState(() {
        _initiatives = _initiatives
            .map((i) => i.id == init.id ? approved : i)
            .toList();
        _isLoading = false;
      });
      widget.onInitiativeApproved?.call(approved);
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _createTask() async {
    final title = _taskTitleController.text.trim();
    if (title.isEmpty) {
      setState(() => _taskError = 'Vui lòng nhập tên công việc');
      return;
    }

    InitiativeModel? targetInit;
    if (!_isBauTask) {
      if (_selectedTaskInitiativeId == null) {
        setState(
          () => _taskError =
              'Vui lòng chọn một Sáng kiến đã được duyệt hoặc đánh dấu là BAU',
        );
        return;
      }

      targetInit = _initiatives.firstWhere(
        (i) => i.id == _selectedTaskInitiativeId,
        orElse: () => throw StateError('Initiative not found'),
      );

      if (!targetInit.isApproved) {
        setState(
          () => _taskError =
              'Sáng kiến "${targetInit!.title}" chưa được phê duyệt (Approval: DRAFT). Không thể gán công việc!',
        );
        return;
      }
    }

    setState(() => _isLoading = true);
    try {
      final taskId = await _service.createExecutionTask(
        title: title,
        initiativeId: targetInit?.id,
      );
      if (!mounted) return;
      setState(() {
        _tasks.add(
          InitiativeTaskItem(
            id: taskId,
            title: title,
            initiativeId: targetInit?.id,
            isBau: _isBauTask,
          ),
        );
        _taskTitleController.clear();
        _taskError = null;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _taskError = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(
                Icons.assignment_turned_in_outlined,
                color: AppTheme.primary,
                size: 20,
              ),
              const SizedBox(width: 8),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Kế Hoạch Sáng Kiến (Initiatives Plan)',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      'Cầu nối trực tiếp giữa OKR và cam kết hành động tuần. Sáng kiến phải được duyệt trước khi gắn việc.',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                key: const ValueKey('open_create_initiative_button'),
                onPressed: () =>
                    setState(() => _showCreateDialog = !_showCreateDialog),
                icon: Icon(
                  _showCreateDialog ? Icons.close : Icons.add,
                  size: 16,
                ),
                label: Text(_showCreateDialog ? 'Hủy' : 'Tạo Sáng Kiến'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.black,
                ),
              ),
            ],
          ),

          if (_errorMessage != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Create Form Dialog / Expandable
          if (_showCreateDialog) ...[
            const SizedBox(height: 16),
            _buildCreateForm(),
          ],

          const SizedBox(height: 16),

          // Initiatives List
          if (_isLoading && _initiatives.isEmpty)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(color: AppTheme.primary),
              ),
            )
          else if (_initiatives.isEmpty)
            Container(
              padding: const EdgeInsets.all(20),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.02),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: AppTheme.borderDark.withValues(alpha: 0.5),
                ),
              ),
              child: const Column(
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    size: 32,
                    color: Colors.white30,
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Chưa có sáng kiến nào được tạo cho mục tiêu này.',
                    style: TextStyle(
                      color: AppTheme.textMutedDark,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            )
          else
            ..._initiatives.map(_buildInitiativeCard),

          const Divider(color: AppTheme.borderDark, height: 32),

          // Downstream Weekly Sprint / Task Planning Section
          _buildWeeklySprintSection(),
        ],
      ),
    );
  }

  Widget _buildCreateForm() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Tạo Sáng Kiến Mới (Bản Nháp)',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.white,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('initiative_title_input'),
            controller: _titleController,
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: const InputDecoration(
              labelText: 'Tiêu đề sáng kiến *',
              hintText: 'VD: Nâng cấp luồng onboarding và hỗ trợ tự động',
              isDense: true,
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            key: const ValueKey('initiative_outcome_input'),
            controller: _outcomeController,
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: const InputDecoration(
              labelText: 'Kết quả kỳ vọng (Intended Outcome)',
              hintText: 'Tăng tỷ lệ hoàn thành onboarding lên 40%',
              isDense: true,
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: TextField(
                  key: const ValueKey('initiative_owner_input'),
                  controller: _ownerController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Người phụ trách (Owner)',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  key: const ValueKey('initiative_target_date_input'),
                  controller: _targetDateController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Ngày hoàn thành mục tiêu',
                    hintText: 'YYYY-MM-DD',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          TextField(
            key: const ValueKey('initiative_milestone_input'),
            controller: _milestoneController,
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: const InputDecoration(
              labelText: 'Cột mốc chính (Milestone)',
              hintText: 'Mốc 1: Ra mắt giao diện mới',
              isDense: true,
              border: OutlineInputBorder(),
            ),
          ),
          if (widget.availableKrIds.isNotEmpty) ...[
            const SizedBox(height: 10),
            const Text(
              'Gắn với Key Results:',
              style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              children: widget.availableKrIds.map((krId) {
                final isSelected = _selectedKrs.contains(krId);
                return FilterChip(
                  label: Text(
                    'KR: $krId',
                    style: const TextStyle(fontSize: 11),
                  ),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      if (selected) {
                        _selectedKrs.add(krId);
                      } else {
                        _selectedKrs.remove(krId);
                      }
                    });
                  },
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => setState(() => _showCreateDialog = false),
                child: const Text('Hủy'),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                key: const ValueKey('submit_create_initiative_button'),
                onPressed: _createInitiativeDraft,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.black,
                ),
                child: const Text('Lưu bản nháp'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInitiativeCard(InitiativeModel init) {
    final isApproved = init.isApproved;
    final downstreamTasks = _tasks
        .where((t) => t.initiativeId == init.id)
        .toList();

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isApproved
              ? Colors.green.withValues(alpha: 0.4)
              : AppTheme.borderDark,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      init.title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    if (init.intendedOutcome != null &&
                        init.intendedOutcome!.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Kỳ vọng: ${init.intendedOutcome}',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textMutedDark,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Status Badge
              Container(
                key: ValueKey('initiative_approval_status_${init.id}'),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isApproved
                      ? Colors.green.withValues(alpha: 0.15)
                      : Colors.amber.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isApproved ? Colors.green : Colors.amber,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      isApproved
                          ? Icons.verified_rounded
                          : Icons.pending_actions_rounded,
                      size: 13,
                      color: isApproved ? Colors.green : Colors.amber,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      isApproved ? 'ĐÃ DUYỆT (APPROVED)' : 'BẢN NHÁP (DRAFT)',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: isApproved ? Colors.green : Colors.amber,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 10),

          // Metadata badges
          Wrap(
            spacing: 12,
            runSpacing: 6,
            children: [
              if (init.ownerMemberId != null && init.ownerMemberId!.isNotEmpty)
                _metaChip(
                  Icons.person_outline,
                  'Phụ trách: ${init.ownerMemberId}',
                ),
              if (init.targetDate != null && init.targetDate!.isNotEmpty)
                _metaChip(
                  Icons.calendar_today_outlined,
                  'Hạn: ${init.targetDate}',
                ),
              if (init.keyResultIds.isNotEmpty)
                _metaChip(
                  Icons.link_rounded,
                  'KRs liên kết: ${init.keyResultIds.join(", ")}',
                ),
              if (init.milestones.isNotEmpty)
                _metaChip(Icons.flag_outlined, 'Mốc: ${init.milestones.first}'),
            ],
          ),

          if (isApproved && init.decisionId != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(
                  Icons.gavel_rounded,
                  size: 14,
                  color: AppTheme.primary,
                ),
                const SizedBox(width: 6),
                Text(
                  'Biên bản quyết định #${init.decisionId} · Phê duyệt bởi: ${init.approvedByMemberId ?? "Founder"}',
                  style: const TextStyle(fontSize: 11, color: AppTheme.primary),
                ),
              ],
            ),
          ],

          const SizedBox(height: 10),

          // Action row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${downstreamTasks.length} việc tuần gắn kết',
                style: const TextStyle(fontSize: 12, color: Colors.white60),
              ),
              if (!isApproved)
                ElevatedButton.icon(
                  key: ValueKey('approve_initiative_button_${init.id}'),
                  onPressed: () => _approveInitiative(init),
                  icon: const Icon(Icons.check_circle_outline, size: 15),
                  label: const Text('Phê duyệt sáng kiến'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    textStyle: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
            ],
          ),

          // Downstream task items
          if (downstreamTasks.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...downstreamTasks.map(
              (t) => Container(
                margin: const EdgeInsets.only(top: 4),
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.04),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_box_outline_blank,
                      size: 14,
                      color: AppTheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        t.title,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    const Text(
                      'Gắn sáng kiến',
                      style: TextStyle(fontSize: 10, color: Colors.green),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _metaChip(IconData icon, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: AppTheme.textMutedDark),
        const SizedBox(width: 4),
        Text(
          text,
          style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
        ),
      ],
    );
  }

  Widget _buildWeeklySprintSection() {
    final bauTasks = _tasks.where((t) => t.isBau).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(
              Icons.directions_run_outlined,
              color: AppTheme.primary,
              size: 18,
            ),
            SizedBox(width: 8),
            Text(
              'Gắn Kết Hành Động Tuần (Weekly Sprint Planning)',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        const Text(
          'Mỗi công việc trong tuần phải gắn với một Sáng kiến đã được duyệt hoặc đánh dấu rõ ràng là công việc thường nhật (BAU).',
          style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
        ),
        const SizedBox(height: 12),

        // Task input row
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: TextField(
                key: const ValueKey('weekly_task_title_input'),
                controller: _taskTitleController,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: const InputDecoration(
                  labelText: 'Tên công việc tuần',
                  hintText: 'VD: Thiết kế mockup luồng onboarding',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 8),
            // Initiative selector
            if (!_isBauTask)
              Expanded(
                flex: 3,
                child: DropdownButtonFormField<String>(
                  key: const ValueKey('task_initiative_dropdown'),
                  isExpanded: true,
                  dropdownColor: AppTheme.surfaceDark,
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                  decoration: const InputDecoration(
                    labelText: 'Chọn sáng kiến',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                  initialValue: _selectedTaskInitiativeId,
                  items: _initiatives.map((init) {
                    final label =
                        '${init.title} (${init.isApproved ? "DUYỆT" : "NHÁP"})';
                    return DropdownMenuItem<String>(
                      value: init.id,
                      child: Text(label, overflow: TextOverflow.ellipsis),
                    );
                  }).toList(),
                  onChanged: (val) =>
                      setState(() => _selectedTaskInitiativeId = val),
                ),
              ),
            const SizedBox(width: 8),
            ElevatedButton(
              key: const ValueKey('assign_task_button'),
              onPressed: _createTask,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
              ),
              child: const Text('Thêm việc'),
            ),
          ],
        ),

        const SizedBox(height: 8),

        // BAU checkbox
        Row(
          children: [
            Checkbox(
              key: const ValueKey('bau_task_checkbox'),
              value: _isBauTask,
              activeColor: AppTheme.primary,
              onChanged: (val) {
                setState(() {
                  _isBauTask = val ?? false;
                  if (_isBauTask) _selectedTaskInitiativeId = null;
                });
              },
            ),
            const Text(
              'Công việc thường nhật (BAU - Business As Usual, không cần sáng kiến)',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        ),

        if (_taskError != null) ...[
          const SizedBox(height: 6),
          Text(
            _taskError!,
            key: const ValueKey('task_assignment_error_message'),
            style: const TextStyle(
              color: Colors.redAccent,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],

        // List BAU tasks
        if (bauTasks.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text(
            'Công việc thường nhật (BAU):',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: Colors.white70,
            ),
          ),
          const SizedBox(height: 4),
          ...bauTasks.map(
            (t) => Container(
              margin: const EdgeInsets.only(top: 4),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(Icons.repeat, size: 14, color: Colors.blueGrey),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      t.title,
                      style: const TextStyle(fontSize: 12, color: Colors.white),
                    ),
                  ),
                  const Text(
                    'BAU',
                    style: TextStyle(fontSize: 10, color: Colors.amberAccent),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}
