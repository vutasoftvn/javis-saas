import 'package:flutter/material.dart';
import '../../../../data/models/twelve_wy_model.dart';
import '../../../../data/services/twelve_wy_service.dart';
import '../../../../data/services/strategy_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../hologram_hub/widgets/twelve_wy/weekly_execution_gauge.dart';
import '../../../hologram_hub/widgets/twelve_wy/tactical_item_card.dart';
import '../../../hologram_hub/widgets/twelve_wy/twelve_week_timeline_bar.dart';

class TwelveWyLoopTab extends StatefulWidget {
  const TwelveWyLoopTab({super.key});

  @override
  State<TwelveWyLoopTab> createState() => _TwelveWyLoopTabState();
}

class _TwelveWyLoopTabState extends State<TwelveWyLoopTab> {
  final _twelveWyService = TwelveWyService();
  final _strategyService = StrategyService();

  List<Map<String, dynamic>> _projects = [];
  int? _selectedProjectId;
  TwelveWyDashboardModel? _dashboard;
  int _selectedWeek = 1;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final projects = await _strategyService.getProjects();
      _projects = projects.cast<Map<String, dynamic>>();
      if (_projects.isNotEmpty) {
        final firstId = int.tryParse(_projects.first['id']?.toString() ?? '') ?? 1;
        _selectedProjectId = firstId;
        await _loadDashboard(firstId);
      }
    } catch (e) {
      debugPrint('[TwelveWyLoopTab] _loadInitialData error: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadDashboard(int projectId) async {
    try {
      final db = await _twelveWyService.getDashboard(projectId);
      if (mounted) {
        setState(() {
          _dashboard = db;
          if (db != null) {
            _selectedWeek = db.currentWeek;
          }
        });
      }
    } catch (e) {
      debugPrint('[TwelveWyLoopTab] _loadDashboard error: $e');
    }
  }

  void _onProjectChanged(int? projectId) {
    if (projectId == null) return;
    setState(() => _selectedProjectId = projectId);
    _loadDashboard(projectId);
  }

  void _showCreateTacticDialog() {
    final titleCtrl = TextEditingController();
    final leadIndicatorCtrl = TextEditingController();
    final targetCtrl = TextEditingController(text: '1');
    int weekNum = _selectedWeek;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Thêm Hành Động Chiến Thuật (Tactic)', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Tên hành động chiến thuật', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: leadIndicatorCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Chỉ số dẫn dắt (Lead Indicator)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: targetCtrl,
                        keyboardType: TextInputType.number,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'Mục tiêu tuần (Target Count)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: weekNum,
                        dropdownColor: const Color(0xFF0F172A),
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'Tuần thực thi', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                        items: List.generate(_dashboard?.cycle.totalWeeks ?? 12, (i) => i + 1).map((w) {
                          return DropdownMenuItem(value: w, child: Text('Tuần $w'));
                        }).toList(),
                        onChanged: (val) => setDialogState(() => weekNum = val ?? 1),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark))),
            ElevatedButton(
              onPressed: () async {
                if (titleCtrl.text.trim().isEmpty || _selectedProjectId == null) return;
                Navigator.pop(ctx);
                final target = int.tryParse(targetCtrl.text.trim()) ?? 1;
                await _twelveWyService.createTactic(
                  projectId: _selectedProjectId!,
                  cycleId: _dashboard?.cycle.id,
                  weekNumber: weekNum,
                  title: titleCtrl.text.trim(),
                  leadIndicatorName: leadIndicatorCtrl.text.trim().isEmpty ? 'Hoàn thành nhiệm vụ' : leadIndicatorCtrl.text.trim(),
                  targetCount: target,
                );
                _loadDashboard(_selectedProjectId!);
              },
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFE879F9), foregroundColor: Colors.black),
              child: const Text('Tạo Tactic'),
            ),
          ],
        ),
      ),
    );
  }

  void _showCreateCycleDialog() {
    final titleCtrl = TextEditingController(text: 'Chiến Dịch 12 Tuần');
    int totalWeeks = 12;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Khởi Tạo Chu Kỳ N-Tuần Mới', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(labelText: 'Tên chu kỳ chiến lược', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  const Text('Thời lượng chu kỳ: ', style: TextStyle(color: Colors.white70)),
                  Text('$totalWeeks tuần', style: const TextStyle(color: Color(0xFFE879F9), fontWeight: FontWeight.bold)),
                ],
              ),
              Slider(
                value: totalWeeks.toDouble(),
                min: 4,
                max: 16,
                divisions: 12,
                activeColor: const Color(0xFFE879F9),
                onChanged: (v) => setDialogState(() => totalWeeks = v.toInt()),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark))),
            ElevatedButton(
              onPressed: () async {
                if (_selectedProjectId == null) return;
                Navigator.pop(ctx);
                await _twelveWyService.createOrGetCycle(_selectedProjectId!, title: titleCtrl.text.trim());
                _loadDashboard(_selectedProjectId!);
              },
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFE879F9), foregroundColor: Colors.black),
              child: const Text('Khởi Tạo'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }

    final db = _dashboard;
    final cycle = db?.cycle;
    final currentWeekTactics = db?.tacticsByWeek[_selectedWeek] ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header Controls
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.borderDark),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<int>(
                    value: _selectedProjectId,
                    hint: const Text('Chọn Dự Án...', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                    dropdownColor: const Color(0xFF0F172A),
                    icon: const Icon(Icons.arrow_drop_down, color: Color(0xFFE879F9), size: 20),
                    items: _projects.map((p) {
                      final id = int.tryParse(p['id']?.toString() ?? '') ?? 0;
                      final title = p['title'] ?? 'Dự án $id';
                      return DropdownMenuItem<int>(
                        value: id,
                        child: Text(title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                      );
                    }).toList(),
                    onChanged: _onProjectChanged,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              if (cycle != null)
                Text(
                  '${cycle.title} • Tuần $_selectedWeek / ${cycle.totalWeeks}',
                  style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                ),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: _showCreateCycleDialog,
                icon: const Icon(Icons.restart_alt, size: 16, color: Color(0xFFE879F9)),
                label: const Text('Khởi Tạo Chu Kỳ Mới', style: TextStyle(color: Color(0xFFE879F9), fontWeight: FontWeight.bold)),
                style: OutlinedButton.styleFrom(side: const BorderSide(color: Color(0xFFE879F9))),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: _showCreateTacticDialog,
                icon: const Icon(Icons.add_task, size: 16),
                label: const Text('Thêm Hành Động Chiến Thuật'),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFE879F9), foregroundColor: Colors.black),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Timeline Bar & Gauge
        if (cycle != null) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.borderDark),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                WeeklyExecutionGauge(
                  score: db?.currentWeekExecutionScore ?? 0.0,
                  weekNumber: _selectedWeek,
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: TwelveWeekTimelineBar(
                    currentWeek: cycle.currentWeek,
                    selectedWeek: _selectedWeek,
                    weeklyScores: db?.weeklyScores ?? {},
                    onSelectWeek: (w) => setState(() => _selectedWeek = w),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],

        // Tactics List for Selected Week
        Expanded(
          child: currentWeekTactics.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.calendar_month_outlined, size: 48, color: AppTheme.textMutedDark),
                      const SizedBox(height: 12),
                      Text('Chưa có hành động chiến thuật nào cho Tuần $_selectedWeek.', style: const TextStyle(color: Colors.white70)),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: _showCreateTacticDialog,
                        icon: const Icon(Icons.add),
                        label: Text('Tạo Tactic cho Tuần $_selectedWeek'),
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFE879F9), foregroundColor: Colors.black),
                      ),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: currentWeekTactics.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final t = currentWeekTactics[index];
                    return TacticalItemCard(
                      tactic: t,
                      onCountChanged: (count) async {
                        await _twelveWyService.updateTactic(tacticId: t.id, actualCount: count);
                        if (_selectedProjectId != null) _loadDashboard(_selectedProjectId!);
                      },
                      onToggleDone: (done) async {
                        final newStatus = done ? 'DONE' : 'IN_PROGRESS';
                        await _twelveWyService.updateTactic(tacticId: t.id, status: newStatus);
                        if (_selectedProjectId != null) _loadDashboard(_selectedProjectId!);
                      },
                    );
                  },
                ),
        ),
      ],
    );
  }
}
