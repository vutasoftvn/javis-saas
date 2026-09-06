import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../models/strategy_workflow_models.dart';
import '../services/strategy_workflow_service.dart';

class WorkspaceStrategySettingsSheet extends StatefulWidget {
  final StrategyWorkflowService? workflowService;
  final VoidCallback? onSettingsUpdated;

  const WorkspaceStrategySettingsSheet({
    super.key,
    this.workflowService,
    this.onSettingsUpdated,
  });

  static Future<void> show(
    BuildContext context, {
    StrategyWorkflowService? workflowService,
    VoidCallback? onSettingsUpdated,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.85,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        builder: (_, scrollController) => WorkspaceStrategySettingsSheet(
          workflowService: workflowService,
          onSettingsUpdated: onSettingsUpdated,
        ),
      ),
    );
  }

  @override
  State<WorkspaceStrategySettingsSheet> createState() => _WorkspaceStrategySettingsSheetState();
}

class _WorkspaceStrategySettingsSheetState extends State<WorkspaceStrategySettingsSheet> {
  late final StrategyWorkflowService _service;
  WorkspaceStrategySettingsModel? _settings;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;
  String? _conflictMessage;

  // Form State
  StrategyMethod _strategyMethod = StrategyMethod.bscFilter;
  BscMode _bscMode = BscMode.required;
  final Set<BscPerspective> _enabledPerspectives = {};
  int _towsLimit = 1;
  bool _weeklyReviewEnabled = true;
  MidCycleReviewPolicy _midCyclePolicy = MidCycleReviewPolicy.auto;
  bool _endCycleReviewEnabled = true;
  final TextEditingController _agentProfilesCtrl = TextEditingController();
  ApprovalPolicy _approvalPolicy = ApprovalPolicy.founderOnly;

  @override
  void initState() {
    super.initState();
    _service = widget.workflowService ?? StrategyWorkflowService();
    _loadSettings();
  }

  @override
  void dispose() {
    _agentProfilesCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadSettings({bool clearConflict = true}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      if (clearConflict) _conflictMessage = null;
    });
    try {
      final s = await _service.getWorkspaceSettings();
      if (mounted) {
        _applySettingsToForm(s);
        setState(() {
          _settings = s;
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

  void _applySettingsToForm(WorkspaceStrategySettingsModel s) {
    _strategyMethod = s.strategyMethod == StrategyMethod.unknown
        ? StrategyMethod.bscFilter
        : s.strategyMethod;
    _bscMode = s.bscMode == BscMode.unknown ? BscMode.required : s.bscMode;
    _enabledPerspectives.clear();
    _enabledPerspectives.addAll(s.enabledBscPerspectives);
    if (_enabledPerspectives.isEmpty) {
      _enabledPerspectives.addAll([
        BscPerspective.financial,
        BscPerspective.customer,
        BscPerspective.internalProcess,
        BscPerspective.learningAndGrowth,
      ]);
    }
    _towsLimit = s.towsSelectionLimit > 0 ? s.towsSelectionLimit : 1;
    _weeklyReviewEnabled = s.weeklyReviewEnabled;
    _midCyclePolicy = s.midCycleReviewPolicy == MidCycleReviewPolicy.unknown
        ? MidCycleReviewPolicy.auto
        : s.midCycleReviewPolicy;
    _endCycleReviewEnabled = s.endCycleReviewEnabled;
    _agentProfilesCtrl.text = s.allowedAgentProfiles.join(', ');
    _approvalPolicy = s.approvalPolicy == ApprovalPolicy.unknown
        ? ApprovalPolicy.founderOnly
        : s.approvalPolicy;
  }

  Future<void> _saveSettings() async {
    if (_settings == null || !_settings!.canEdit) return;

    setState(() {
      _isSaving = true;
      _errorMessage = null;
      _conflictMessage = null;
    });

    final rawAgents = _agentProfilesCtrl.text
        .split(',')
        .map((a) => a.trim())
        .where((a) => a.isNotEmpty)
        .toList();

    try {
      final updated = await _service.updateWorkspaceSettings(
        strategyMethod: _strategyMethod,
        bscMode: _bscMode,
        enabledBscPerspectives: _enabledPerspectives.toList(),
        towsSelectionLimit: _towsLimit,
        weeklyReviewEnabled: _weeklyReviewEnabled,
        midCycleReviewPolicy: _midCyclePolicy,
        endCycleReviewEnabled: _endCycleReviewEnabled,
        allowedAgentProfiles: rawAgents,
        approvalPolicy: _approvalPolicy,
        expectedRevision: _settings!.revision,
      );

      if (mounted) {
        _applySettingsToForm(updated);
        setState(() {
          _settings = updated;
          _isSaving = false;
        });
        widget.onSettingsUpdated?.call();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã lưu cấu hình chiến lược thành công')),
        );
      }
    } on RevisionConflictException catch (_) {
      // Handle 409 conflict by reloading instead of overwriting
      if (mounted) {
        setState(() {
          _conflictMessage =
              'Xung đột phiên bản (409): Cấu hình đã được cập nhật bởi quản trị viên khác. Đang tải lại dữ liệu mới nhất...';
          _isSaving = false;
        });
        // Reload fresh settings from server without clearing conflict message
        await _loadSettings(clearConflict: false);
      }
    } catch (e) {
      if (e.toString().contains('409') || e.toString().contains('Revision conflict')) {
        if (mounted) {
          setState(() {
            _conflictMessage =
                'Xung đột phiên bản (409): Cấu hình đã được cập nhật bởi quản trị viên khác. Đang tải lại dữ liệu mới nhất...';
            _isSaving = false;
          });
          await _loadSettings(clearConflict: false);
        }
      } else if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isSaving = false;
        });
      }
    }
  }


  @override
  Widget build(BuildContext context) {
    final canEdit = _settings?.canEdit ?? true;

    return Material(
      color: AppTheme.surfaceDark,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
      child: Column(
        children: [
          // Header handle & title
          Container(

            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
            ),
            child: Row(
              children: [
                const Icon(Icons.tune_rounded, color: AppTheme.primary, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Cài Đặt Khung Quản Trị Chiến Lược (Strategy Settings)',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      Text(
                        _settings != null
                            ? 'Phiên bản chính sách: rev ${_settings!.revision} · ${canEdit ? "Quyền quản trị" : "Chỉ xem"}'
                            : 'Đang tải cấu hình...',
                        style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          // Body
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                : ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      // Read-only notice
                      if (!canEdit)
                        Container(
                          key: const ValueKey('settings_read_only_banner'),
                          margin: const EdgeInsets.only(bottom: 16),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.amber.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.amber.withValues(alpha: 0.4)),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.lock_outline, color: Colors.amber, size: 20),
                              SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'Chế độ chỉ đọc: Bạn không có quyền quản lý khung chiến lược (strategy.framework.manage). Liên hệ Founder để được cấp quyền sửa đổi.',
                                  style: TextStyle(color: Colors.amber, fontSize: 12),
                                ),
                              ),
                            ],
                          ),
                        ),

                      // Conflict message
                      if (_conflictMessage != null)
                        Container(
                          key: const ValueKey('settings_conflict_banner'),
                          margin: const EdgeInsets.only(bottom: 16),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.orange.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.orange),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.sync_problem_rounded, color: Colors.orange, size: 20),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _conflictMessage!,
                                  style: const TextStyle(color: Colors.orange, fontSize: 12, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                        ),

                      if (_errorMessage != null)
                        Container(
                          margin: const EdgeInsets.only(bottom: 16),
                          padding: const EdgeInsets.all(12),
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
                                child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 12)),
                              ),
                            ],
                          ),
                        ),

                      // 1. Strategy Method
                      _buildSectionTitle('1. Phương Pháp Luận Chiến Lược'),
                      DropdownButtonFormField<StrategyMethod>(
                        key: const ValueKey('settings_strategy_method_dropdown'),
                        initialValue: _strategyMethod,
                        dropdownColor: AppTheme.surfaceDarkLighter,
                        decoration: const InputDecoration(
                          labelText: 'Phương pháp phân tích',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: StrategyMethod.bscFilter,
                            child: Text('BSC Filtered (Được điều hướng bởi 4 góc nhìn BSC)', style: TextStyle(color: Colors.white, fontSize: 13)),
                          ),
                          DropdownMenuItem(
                            value: StrategyMethod.classic,
                            child: Text('Classic (Phân tích truyền thống)', style: TextStyle(color: Colors.white, fontSize: 13)),
                          ),
                        ],
                        onChanged: canEdit ? (val) => setState(() => _strategyMethod = val!) : null,
                      ),

                      const SizedBox(height: 16),

                      // 2. BSC Mode & Perspectives
                      _buildSectionTitle('2. Chế Độ Thẻ Điểm Cân Bằng (BSC Mode)'),
                      DropdownButtonFormField<BscMode>(
                        key: const ValueKey('settings_bsc_mode_dropdown'),
                        initialValue: _bscMode,
                        dropdownColor: AppTheme.surfaceDarkLighter,
                        decoration: const InputDecoration(
                          labelText: 'Mức độ bắt buộc BSC',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: BscMode.required,
                            child: Text('Bắt buộc (REQUIRED - Chặn phân tích nếu chưa chọn góc nhìn)', style: TextStyle(color: Colors.white, fontSize: 13)),
                          ),
                          DropdownMenuItem(
                            value: BscMode.optional,
                            child: Text('Tùy chọn (OPTIONAL - Có thể bỏ qua bước chọn góc nhìn)', style: TextStyle(color: Colors.white, fontSize: 13)),
                          ),
                          DropdownMenuItem(
                            value: BscMode.off,
                            child: Text('Tắt hoàn toàn (OFF - Không dùng BSC)', style: TextStyle(color: Colors.white, fontSize: 13)),
                          ),
                        ],
                        onChanged: canEdit ? (val) => setState(() => _bscMode = val!) : null,
                      ),

                      if (_bscMode != BscMode.off) ...[
                        const SizedBox(height: 12),
                        const Text(
                          'Các góc nhìn BSC được kích hoạt:',
                          style: TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          children: [
                            BscPerspective.financial,
                            BscPerspective.customer,
                            BscPerspective.internalProcess,
                            BscPerspective.learningAndGrowth,
                          ].map((p) {
                            final isChecked = _enabledPerspectives.contains(p);
                            return FilterChip(
                              key: ValueKey('settings_bsc_chip_${p.toApiString()}'),
                              label: Text(p.displayNameVi, style: const TextStyle(fontSize: 12)),
                              selected: isChecked,
                              onSelected: canEdit
                                  ? (selected) {
                                      setState(() {
                                        if (selected) {
                                          _enabledPerspectives.add(p);
                                        } else {
                                          _enabledPerspectives.remove(p);
                                        }
                                      });
                                    }
                                  : null,
                            );
                          }).toList(),
                        ),
                      ],

                      const SizedBox(height: 20),

                      // 3. TOWS Selection Limit
                      _buildSectionTitle('3. Giới Hạn Lựa Chọn Chiến Lược TOWS'),
                      DropdownButtonFormField<int>(
                        key: const ValueKey('settings_tows_limit_dropdown'),
                        initialValue: _towsLimit,
                        dropdownColor: AppTheme.surfaceDarkLighter,
                        decoration: const InputDecoration(
                          labelText: 'Số lượng phương án TOWS tối đa được chọn',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 1, child: Text('1 chiến lược trọng tâm (Tập trung tối đa)', style: TextStyle(color: Colors.white, fontSize: 13))),
                          DropdownMenuItem(value: 2, child: Text('2 chiến lược song song', style: TextStyle(color: Colors.white, fontSize: 13))),
                          DropdownMenuItem(value: 3, child: Text('3 chiến lược', style: TextStyle(color: Colors.white, fontSize: 13))),
                        ],
                        onChanged: canEdit ? (val) => setState(() => _towsLimit = val ?? 1) : null,
                      ),

                      const SizedBox(height: 20),

                      // 4. Review Policy
                      _buildSectionTitle('4. Chính Sách Đánh Giá Chu Kỳ (Review Policy)'),
                      SwitchListTile(
                        key: const ValueKey('settings_weekly_review_switch'),
                        title: const Text('Đánh giá hàng tuần (Weekly Review)', style: TextStyle(color: Colors.white, fontSize: 13)),
                        subtitle: const Text('Lên lịch và theo dõi tiến độ công việc tuần', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
                        value: _weeklyReviewEnabled,
                        activeThumbColor: AppTheme.primary,
                        onChanged: canEdit ? (val) => setState(() => _weeklyReviewEnabled = val) : null,
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<MidCycleReviewPolicy>(
                        key: const ValueKey('settings_mid_cycle_dropdown'),
                        initialValue: _midCyclePolicy,
                        dropdownColor: AppTheme.surfaceDarkLighter,
                        decoration: const InputDecoration(
                          labelText: 'Đánh giá giữa chu kỳ (Mid-cycle Review)',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: MidCycleReviewPolicy.auto, child: Text('Tự động lên lịch (Tuần giữa chu kỳ)', style: TextStyle(color: Colors.white, fontSize: 13))),
                          DropdownMenuItem(value: MidCycleReviewPolicy.custom, child: Text('Tùy chỉnh lịch (Custom week)', style: TextStyle(color: Colors.white, fontSize: 13))),
                          DropdownMenuItem(value: MidCycleReviewPolicy.off, child: Text('Tắt đánh giá giữa chu kỳ', style: TextStyle(color: Colors.white, fontSize: 13))),
                        ],
                        onChanged: canEdit ? (val) => setState(() => _midCyclePolicy = val!) : null,
                      ),
                      const SizedBox(height: 8),
                      SwitchListTile(
                        key: const ValueKey('settings_end_cycle_switch'),
                        title: const Text('Đánh giá cuối chu kỳ (End-cycle Review)', style: TextStyle(color: Colors.white, fontSize: 13)),
                        subtitle: const Text('Tổng kết chu kỳ và chốt biên bản quyết định quản trị', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
                        value: _endCycleReviewEnabled,
                        activeThumbColor: AppTheme.primary,
                        onChanged: canEdit ? (val) => setState(() => _endCycleReviewEnabled = val) : null,
                      ),

                      const SizedBox(height: 20),

                      // 5. Agent Profiles & Approval Policy
                      _buildSectionTitle('5. Phân Quyền Phê Duyệt & Tác Nhân AI'),
                      DropdownButtonFormField<ApprovalPolicy>(
                        key: const ValueKey('settings_approval_policy_dropdown'),
                        initialValue: _approvalPolicy,
                        dropdownColor: AppTheme.surfaceDarkLighter,
                        decoration: const InputDecoration(
                          labelText: 'Chính sách phê duyệt sáng kiến & OKR',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: ApprovalPolicy.founderOnly, child: Text('Chỉ Founder (Founder-only approval)', style: TextStyle(color: Colors.white, fontSize: 13))),
                          DropdownMenuItem(value: ApprovalPolicy.delegatedApprover, child: Text('Người được ủy quyền (Delegated Approver)', style: TextStyle(color: Colors.white, fontSize: 13))),
                        ],
                        onChanged: canEdit ? (val) => setState(() => _approvalPolicy = val!) : null,
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        key: const ValueKey('settings_agent_profiles_input'),
                        controller: _agentProfilesCtrl,
                        enabled: canEdit,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: const InputDecoration(
                          labelText: 'Hồ sơ Agent được phép tham gia (cách nhau dấu phẩy)',
                          hintText: 'VD: strategic_copilot, bsc_evaluator',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ],
                  ),
          ),

          // Footer
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppTheme.borderDark)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Đóng'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  key: const ValueKey('settings_save_button'),
                  onPressed: canEdit && !_isSaving ? _saveSettings : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  ),
                  child: _isSaving
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                        )
                      : const Text('Lưu thay đổi'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.bold,
          color: AppTheme.primary,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}
