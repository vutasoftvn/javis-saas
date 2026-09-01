import 'package:flutter/material.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../../../data/models/twelve_wy_model.dart';
import '../../../../modules/strategy/services/twelve_wy_service.dart';
import 'weekly_execution_gauge.dart';
import 'tactical_item_card.dart';
import 'twelve_week_timeline_bar.dart';

class TwelveWyHubModal extends StatefulWidget {
  final int projectId;
  final TwelveWyDashboardModel? initialDashboard;

  const TwelveWyHubModal({
    super.key,
    required this.projectId,
    this.initialDashboard,
  });

  static Future<void> show(
    BuildContext context, {
    required int projectId,
    TwelveWyDashboardModel? dashboard,
  }) {
    return showDialog<void>(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (_) => TwelveWyHubModal(
        projectId: projectId,
        initialDashboard: dashboard,
      ),
    );
  }

  @override
  State<TwelveWyHubModal> createState() => _TwelveWyHubModalState();
}

class _TwelveWyHubModalState extends State<TwelveWyHubModal>
    with SingleTickerProviderStateMixin {
  final _service = TwelveWyService();
  late TabController _tabController;
  int _selectedWeek = 1;

  TwelveWyDashboardModel? _dashboard;
  bool _isLoading = true;
  bool _isCreatingTactic = false;

  // New Tactic form
  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _leadNameCtrl = TextEditingController();
  final _targetCtrl = TextEditingController(text: '1');
  final _ownerCtrl = TextEditingController(text: 'Founder');
  int _weekForNewTactic = 1;

  // Cycle creation
  final _cycleTitleCtrl = TextEditingController();
  int _customTotalWeeks = 12;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _dashboard = widget.initialDashboard;
    _isLoading = _dashboard == null;
    _selectedWeek = _dashboard?.currentWeek ?? 1;
    _weekForNewTactic = _selectedWeek;
    if (_isLoading) _loadDashboard();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _titleCtrl.dispose();
    _descCtrl.dispose();
    _leadNameCtrl.dispose();
    _targetCtrl.dispose();
    _ownerCtrl.dispose();
    _cycleTitleCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadDashboard() async {
    setState(() => _isLoading = true);
    final d = await _service.getDashboard(widget.projectId);
    if (mounted) {
      setState(() {
        _dashboard = d;
        _selectedWeek = d?.currentWeek ?? 1;
        _weekForNewTactic = _selectedWeek;
        _isLoading = false;
      });
    }
  }

  Future<void> _createCycle() async {
    final title = _cycleTitleCtrl.text.trim().isEmpty
        ? 'Chu Kỳ Thực Thi $_customTotalWeeks Tuần'
        : _cycleTitleCtrl.text.trim();
    await _service.createOrGetCycle(widget.projectId, title: title);
    _loadDashboard();
  }

  Future<void> _addTactic() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isCreatingTactic = true);
    await _service.createTactic(
      projectId: widget.projectId,
      cycleId: _dashboard?.cycle.id,
      weekNumber: _weekForNewTactic,
      title: _titleCtrl.text.trim(),
      description: _descCtrl.text.trim(),
      leadIndicatorName: _leadNameCtrl.text.trim().isEmpty
          ? 'Lead Indicator'
          : _leadNameCtrl.text.trim(),
      targetCount: int.tryParse(_targetCtrl.text) ?? 1,
      ownerRole: _ownerCtrl.text.trim().isEmpty ? 'Founder' : _ownerCtrl.text.trim(),
    );
    _titleCtrl.clear();
    _descCtrl.clear();
    _leadNameCtrl.clear();
    _targetCtrl.text = '1';
    setState(() => _isCreatingTactic = false);
    _loadDashboard();
    if (mounted) {
      AppToast.success(
        'Đã thêm Tactic mới',
        duration: const Duration(seconds: 2),
      );
    }
  }

  Future<void> _updateTacticCount(TacticalItemModel tactic, int newCount) async {
    await _service.updateTactic(tacticId: tactic.id, actualCount: newCount);
    _loadDashboard();
  }

  Future<void> _toggleTacticDone(TacticalItemModel tactic, bool done) async {
    await _service.updateTactic(
      tacticId: tactic.id,
      status: done ? 'DONE' : 'IN_PROGRESS',
    );
    _loadDashboard();
  }

  Future<void> _generateReview() async {
    if (_dashboard == null) return;
    await _service.generateWeeklyReview(
      cycleId: _dashboard!.cycle.id,
      weekNumber: _selectedWeek,
    );
    _loadDashboard();
    _tabController.animateTo(2);
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820, maxHeight: 700),
        child: Container(
          decoration: BoxDecoration(
            color: const Color(0xFF0D1625),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.35)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFF59E0B).withValues(alpha: 0.1),
                blurRadius: 40,
                spreadRadius: 4,
              ),
            ],
          ),
          child: Column(
            children: [
              _buildHeader(),
              if (!_isLoading && _dashboard != null) ...[
                _buildTimeline(),
                _buildTabs(),
                Expanded(child: _buildTabContent()),
              ] else if (_isLoading) ...[
                const Expanded(
                  child: Center(
                    child: CircularProgressIndicator(color: Color(0xFFF59E0B)),
                  ),
                ),
              ] else ...[
                Expanded(child: _buildCreateCyclePrompt()),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final cycle = _dashboard?.cycle;
    final score = _dashboard?.currentWeekExecutionScore ?? 0.0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: Colors.white.withValues(alpha: 0.08))),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.calendar_month_outlined, color: Color(0xFFF59E0B), size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  cycle?.title ?? 'Vòng Lặp Thực Thi ${cycle?.totalWeeks ?? _customTotalWeeks} Tuần',
                  style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  cycle != null
                      ? 'Tuần ${cycle.currentWeek}/${cycle.totalWeeks} · Điểm Thực Thi: ${score.toStringAsFixed(1)}%'
                      : 'Chưa khởi tạo chu kỳ — User có thể tự chọn số tuần',
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          if (_dashboard != null)
            TextButton.icon(
              onPressed: _generateReview,
              icon: const Icon(Icons.summarize_outlined, size: 16, color: Color(0xFFF59E0B)),
              label: const Text('Tổng Kết WAM', style: TextStyle(color: Color(0xFFF59E0B), fontSize: 12)),
              style: TextButton.styleFrom(
                backgroundColor: const Color(0xFFF59E0B).withValues(alpha: 0.1),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.close, color: Colors.white54),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeline() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TwelveWeekTimelineBar(
            currentWeek: _dashboard!.currentWeek,
            selectedWeek: _selectedWeek,
            weeklyScores: _dashboard!.weeklyScores,
            onSelectWeek: (w) {
              setState(() {
                _selectedWeek = w;
                _weekForNewTactic = w;
              });
            },
          ),
          const SizedBox(height: 10),
          WeeklyExecutionGauge(
            score: _dashboard!.weeklyScores[_selectedWeek] ?? 0.0,
            weekNumber: _selectedWeek,
          ),
        ],
      ),
    );
  }

  Widget _buildTabs() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(10),
      ),
      child: TabBar(
        controller: _tabController,
        indicator: BoxDecoration(
          color: const Color(0xFFF59E0B).withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.4)),
        ),
        labelColor: const Color(0xFFF59E0B),
        unselectedLabelColor: Colors.white60,
        labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
        tabs: const [
          Tab(text: 'Tactics Tuần'),
          Tab(text: '+ Thêm Tactic'),
          Tab(text: 'Kiểm Điểm WAM'),
        ],
      ),
    );
  }

  Widget _buildTabContent() {
    return TabBarView(
      controller: _tabController,
      children: [
        _buildTacticsTab(),
        _buildAddTacticTab(),
        _buildWamReviewTab(),
      ],
    );
  }

  Widget _buildTacticsTab() {
    final tactics = _dashboard!.tacticsByWeek[_selectedWeek] ?? [];
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: tactics.isEmpty
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.inbox_outlined, color: Colors.white24, size: 48),
                  const SizedBox(height: 12),
                  Text('Chưa có Tactics nào cho Tuần $_selectedWeek',
                      style: const TextStyle(color: Colors.white54, fontSize: 13)),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => _tabController.animateTo(1),
                    child: const Text('+ Thêm Tactic ngay', style: TextStyle(color: Color(0xFFF59E0B))),
                  ),
                ],
              ),
            )
          : ListView.builder(
              itemCount: tactics.length,
              itemBuilder: (_, i) => TacticalItemCard(
                tactic: tactics[i],
                onCountChanged: (v) => _updateTacticCount(tactics[i], v),
                onToggleDone: (done) => _toggleTacticDone(tactics[i], done),
              ),
            ),
    );
  }

  Widget _buildAddTacticTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _sectionLabel('Tuần thực hiện'),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: List.generate(_dashboard!.cycle.totalWeeks, (i) {
                final w = i + 1;
                final isSelected = w == _weekForNewTactic;
                return InkWell(
                  onTap: () => setState(() => _weekForNewTactic = w),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? const Color(0xFFF59E0B).withValues(alpha: 0.25)
                          : Colors.white.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: isSelected ? const Color(0xFFF59E0B) : Colors.white24,
                      ),
                    ),
                    child: Text('W$w',
                        style: TextStyle(
                          color: isSelected ? const Color(0xFFF59E0B) : Colors.white70,
                          fontSize: 12,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        )),
                  ),
                );
              }),
            ),
            const SizedBox(height: 14),
            _sectionLabel('Tiêu đề hành động *'),
            const SizedBox(height: 6),
            _inputField(_titleCtrl, 'Vd: Phỏng vấn 10 founder về quy trình lập kế hoạch', required: true),
            const SizedBox(height: 10),
            _sectionLabel('Mô tả (tuỳ chọn)'),
            const SizedBox(height: 6),
            _inputField(_descCtrl, 'Chi tiết thêm về cách thực hiện...', maxLines: 2),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                flex: 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _sectionLabel('Tên Lead Indicator *'),
                    const SizedBox(height: 6),
                    _inputField(_leadNameCtrl, 'Vd: Số cuộc gọi, Số bản prototype', required: true),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _sectionLabel('Target Count *'),
                    const SizedBox(height: 6),
                    _inputField(_targetCtrl, '10', isNumber: true, required: true),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _sectionLabel('Người Sở Hữu'),
                    const SizedBox(height: 6),
                    _inputField(_ownerCtrl, 'Founder'),
                  ],
                ),
              ),
            ]),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isCreatingTactic ? null : _addTactic,
              icon: _isCreatingTactic
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.add_task, size: 18),
              label: Text(_isCreatingTactic ? 'Đang lưu...' : 'Thêm Tactic vào Tuần $_weekForNewTactic'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFF59E0B),
                foregroundColor: const Color(0xFF0D1625),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWamReviewTab() {
    final review = _dashboard?.latestReview;
    if (review == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.summarize_outlined, color: Colors.white24, size: 48),
            const SizedBox(height: 12),
            const Text('Chưa có bản tổng kết WAM nào.', style: TextStyle(color: Colors.white54)),
            const SizedBox(height: 8),
            TextButton(
              onPressed: _generateReview,
              child: const Text('Tổng kết tuần này ngay', style: TextStyle(color: Color(0xFFF59E0B))),
            ),
          ],
        ),
      );
    }

    Color scoreColor = const Color(0xFFEF4444);
    if (review.executionScore >= 85.0) scoreColor = const Color(0xFF10B981);
    if (review.executionScore >= 60.0 && review.executionScore < 85.0) scoreColor = const Color(0xFFF59E0B);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Score Banner
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: scoreColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: scoreColor.withValues(alpha: 0.4)),
            ),
            child: Row(
              children: [
                Text(
                  '${review.executionScore.toStringAsFixed(1)}%',
                  style: TextStyle(color: scoreColor, fontSize: 32, fontWeight: FontWeight.bold),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Tuần ${review.weekNumber} — Điểm Thực Thi',
                          style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                      Text(
                          '${review.totalCompleted}/${review.totalPlanned} Tactics hoàn thành',
                          style: const TextStyle(color: Colors.white60, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),

          if (review.keyBreakthroughs.isNotEmpty) ...[
            const SizedBox(height: 14),
            _reviewSection('🏆 Thành Tựu Đạt Được', review.keyBreakthroughs, const Color(0xFF10B981)),
          ],
          if (review.rootCauseBlocks.isNotEmpty) ...[
            const SizedBox(height: 14),
            _reviewSection('🚧 Điểm Nghẽn Gốc Rễ', review.rootCauseBlocks, const Color(0xFFEF4444)),
          ],
          if (review.aiRecommendations.isNotEmpty) ...[
            const SizedBox(height: 14),
            _reviewSection('🤖 Khuyến Nghị AI', review.aiRecommendations, const Color(0xFF38BDF8)),
          ],
        ],
      ),
    );
  }

  Widget _buildCreateCyclePrompt() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const Icon(Icons.loop, color: Color(0xFFF59E0B), size: 56),
          const SizedBox(height: 16),
          const Text(
            'Bắt Đầu Vòng Lặp Thực Thi Mới',
            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Khởi tạo chu kỳ với số tuần bạn tự chọn (2–52 tuần) dựa trên nhịp độ thực tế của dự án.',
            style: TextStyle(color: Colors.white60, fontSize: 13, height: 1.5),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          // Số tuần picker
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('Số tuần trong chu kỳ:', style: TextStyle(color: Colors.white70)),
              const SizedBox(width: 12),
              DropdownButton<int>(
                value: _customTotalWeeks,
                dropdownColor: const Color(0xFF1E293B),
                items: [2, 4, 6, 8, 10, 12, 16, 20, 24, 52]
                    .map((w) => DropdownMenuItem<int>(
                          value: w,
                          child: Text('$w tuần', style: const TextStyle(color: Colors.white)),
                        ))
                    .toList(),
                onChanged: (v) => setState(() => _customTotalWeeks = v ?? 12),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _inputField(_cycleTitleCtrl, 'Tiêu đề chu kỳ (tuỳ chọn)', maxLines: 1),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: _createCycle,
            icon: const Icon(Icons.rocket_launch_outlined, size: 18),
            label: Text('Bắt Đầu Chu Kỳ $_customTotalWeeks Tuần'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFF59E0B),
              foregroundColor: const Color(0xFF0D1625),
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 24),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  // --- Helpers ---
  Widget _sectionLabel(String text) => Text(
        text,
        style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w600),
      );

  Widget _inputField(
    TextEditingController ctrl,
    String hint, {
    bool required = false,
    bool isNumber = false,
    int maxLines = 1,
  }) {
    return TextFormField(
      controller: ctrl,
      maxLines: maxLines,
      keyboardType: isNumber ? TextInputType.number : TextInputType.text,
      style: const TextStyle(color: Colors.white, fontSize: 13),
      validator: required
          ? (v) => (v == null || v.trim().isEmpty) ? 'Bắt buộc' : null
          : null,
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Colors.white30, fontSize: 12),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.06),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFFF59E0B)),
        ),
      ),
    );
  }

  Widget _reviewSection(String title, List<String> items, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(title, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        ...items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.circle, color: color, size: 7),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(item,
                        style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.4)),
                  ),
                ],
              ),
            )),
      ],
    );
  }
}
