import 'package:flutter/material.dart';
import '../../../../core/network/api_result.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/mvp_strategy_models.dart';
import '../../services/twelve_wy_service.dart';

/// Tab "Review tuần" — chấm executionScore/outcomeScore/reflection cho 1
/// weekly plan đã tồn tại. Đọc plan.md
/// (docs/superpowers/plans/2026-09-03-weekly-review-tab.md) Task 4.
class WeeklyReviewTab extends StatefulWidget {
  const WeeklyReviewTab({super.key, this.service});

  /// Cho phép tiêm `TwelveWyService` giả trong test — mặc định `null` sẽ
  /// dùng `TwelveWyService()` thật (theo đúng pattern DI đã dùng ở
  /// `WorkspaceOrientationSettingsCard`). Bắt buộc phải tiêm khi test vì
  /// `TwelveWyService()` mặc định dựng `MvpRequestClient` với `http.Client()`
  /// thật riêng, không đọc qua `ApiClient.client` — override
  /// `ApiClient.client` trong test không có tác dụng với đường MVP này.
  final TwelveWyService? service;

  @override
  State<WeeklyReviewTab> createState() => _WeeklyReviewTabState();
}

class _WeeklyReviewTabState extends State<WeeklyReviewTab> {
  late final TwelveWyService _service;
  bool _isLoading = true;
  String? _error;
  List<MvpWeeklyPlan> _plans = [];
  List<MvpWeeklyCommitment> _commitments = [];
  MvpWeeklyPlan? _selectedPlan;

  final _executionCtrl = TextEditingController();
  final _outcomeCtrl = TextEditingController();
  final _reflectionCtrl = TextEditingController();
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? TwelveWyService();
    _load();
  }

  @override
  void dispose() {
    _executionCtrl.dispose();
    _outcomeCtrl.dispose();
    _reflectionCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    final plansResult = await _service.getWeeklyPlans();
    final commitmentsResult = await _service.getWeeklyCommitments();

    if (plansResult is ApiSuccess<List<MvpWeeklyPlan>>) {
      _plans = plansResult.data;
    } else {
      _error = 'Không tải được danh sách tuần';
    }
    if (commitmentsResult is ApiSuccess<List<MvpWeeklyCommitment>>) {
      _commitments = commitmentsResult.data;
    }

    if (_plans.isNotEmpty) {
      _selectedPlan = _plans.reduce((a, b) => a.weekNo >= b.weekNo ? a : b);
      _executionCtrl.text = _selectedPlan?.executionScore?.toString() ?? '';
      _outcomeCtrl.text = _selectedPlan?.outcomeScore?.toString() ?? '';
      _reflectionCtrl.text = _selectedPlan?.reflection ?? '';
    }

    if (!mounted) return;
    setState(() => _isLoading = false);
  }

  List<MvpWeeklyCommitment> get _commitmentsForSelectedPlan {
    final planId = _selectedPlan?.id;
    if (planId == null) return [];
    return _commitments.where((c) => c.weeklyPlanId == planId).toList();
  }

  Future<void> _save() async {
    final plan = _selectedPlan;
    if (plan == null) return;
    setState(() => _isSaving = true);
    final result = await _service.updateWeeklyPlan(
      id: plan.id,
      executionScore: double.tryParse(_executionCtrl.text),
      outcomeScore: double.tryParse(_outcomeCtrl.text),
      reflection: _reflectionCtrl.text.trim().isEmpty
          ? null
          : _reflectionCtrl.text.trim(),
    );
    if (!mounted) return;
    setState(() => _isSaving = false);
    if (result is ApiSuccess<MvpWeeklyPlan>) {
      setState(() {
        final idx = _plans.indexWhere((p) => p.id == plan.id);
        if (idx != -1) _plans[idx] = result.data;
        _selectedPlan = result.data;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Text(_error!, style: const TextStyle(color: AppTheme.error)),
      );
    }
    if (_plans.isEmpty) {
      return const Center(
        child: Text(
          'Chưa có tuần nào để review. Kickoff dự án trước để tạo tuần 1.',
          style: TextStyle(color: AppTheme.textMutedDark),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButton<String>(
            value: _selectedPlan?.id,
            items: _plans
                .map(
                  (p) => DropdownMenuItem(
                    value: p.id,
                    child: Text(
                      'Tuần ${p.weekNo}${p.focus != null ? " — ${p.focus}" : ""}',
                    ),
                  ),
                )
                .toList(),
            onChanged: (id) {
              final plan = _plans.firstWhere((p) => p.id == id);
              setState(() {
                _selectedPlan = plan;
                _executionCtrl.text = plan.executionScore?.toString() ?? '';
                _outcomeCtrl.text = plan.outcomeScore?.toString() ?? '';
                _reflectionCtrl.text = plan.reflection ?? '';
              });
            },
          ),
          const SizedBox(height: 16),
          if (_selectedPlan?.focus != null)
            Text(
              _selectedPlan!.focus!,
              style: const TextStyle(
                color: AppTheme.textDark,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          const SizedBox(height: 16),
          const Text(
            'Cam kết tuần này',
            style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          for (final c in _commitmentsForSelectedPlan)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Icon(
                    c.status == 'done'
                        ? Icons.check_circle
                        : Icons.radio_button_unchecked,
                    size: 16,
                    color: c.status == 'done'
                        ? AppTheme.success
                        : AppTheme.textMutedDark,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      c.title,
                      style: const TextStyle(color: AppTheme.textDark),
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 20),
          TextField(
            key: const Key('execution_score_field'),
            controller: _executionCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Điểm thực thi (0-100)'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('outcome_score_field'),
            controller: _outcomeCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Điểm kết quả (0-100)'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('reflection_field'),
            controller: _reflectionCtrl,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Ghi chú / bài học tuần này',
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _isSaving ? null : _save,
            child: Text(_isSaving ? 'Đang lưu...' : 'Lưu review'),
          ),
        ],
      ),
    );
  }
}
