import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/stage_model.dart';
import '../../../../data/models/strategy_lens_model.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../modules/strategy/services/strategy_lens_service.dart';
import '../../../../modules/strategy/services/strategy_service.dart';
import '../../../../modules/vault/services/evidence_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../hologram_hub/widgets/lenses/pestel_radar_widget.dart';
import '../../../hologram_hub/widgets/lenses/swot_evidence_grid_widget.dart';
import '../../../hologram_hub/widgets/lenses/tows_matrix_widget.dart';
import '../../../hologram_hub/widgets/lenses/bsc_scorecard_widget.dart';
import '../../../../shared/widgets/stage_badge.dart';

class StrategyLensesTab extends StatefulWidget {
  const StrategyLensesTab({super.key});

  @override
  State<StrategyLensesTab> createState() => _StrategyLensesTabState();
}

class _StrategyLensesTabState extends State<StrategyLensesTab> with SingleTickerProviderStateMixin {
  final _lensService = StrategyLensService();
  final _strategyService = StrategyService();
  final _evidenceService = EvidenceService();
  late TabController _tabController;

  List<Map<String, dynamic>> _projects = [];
  int? _selectedProjectId;
  ProjectStage _currentStage = ProjectStage.p1ProblemValidation;
  StageLensSummaryModel? _summary;
  List<EvidenceModel> _evidences = [];
  bool _isLoading = true;
  String? _projectsError;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadInitialData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final result = await _strategyService.getProjects();
      _projects = result.items;
      _projectsError = result.errorMessage;
      if (_projects.isNotEmpty) {
        final firstId = int.tryParse(_projects.first['id']?.toString() ?? '') ?? 1;
        _selectedProjectId = firstId;
        final rawStage = _projects.first['project_stage']?.toString();
        _currentStage = ProjectStage.fromString(rawStage);
        await _loadLensData(firstId);
      }
    } catch (e) {
      debugPrint('[StrategyLensesTab] _loadInitialData error: $e');
      _projectsError = 'Không thể tải danh sách dự án: $e';
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadLensData(int projectId) async {
    try {
      final summary = await _lensService.getStageLensSummary(projectId);
      final evidences = await _evidenceService.getEvidences(projectId: projectId);
      if (mounted) {
        setState(() {
          _summary = summary;
          _evidences = evidences;
        });
      }
    } catch (e) {
      debugPrint('[StrategyLensesTab] _loadLensData error: $e');
    }
  }

  void _onProjectChanged(int? projectId) {
    if (projectId == null) return;
    final proj = _projects.firstWhereOrNull((p) => (int.tryParse(p['id']?.toString() ?? '') ?? 0) == projectId);
    setState(() {
      _selectedProjectId = projectId;
      if (proj != null) {
        _currentStage = ProjectStage.fromString(proj['project_stage']?.toString());
      }
    });
    _loadLensData(projectId);
  }

  // Danh sách dự án tải thất bại (401/403/409/5xx, JSON hỏng, mất mạng...)
  // trước đây bị nuốt thành `[]` và tab hiển thị y hệt "chưa có dự án nào" —
  // giờ hiện banner lỗi kèm nút thử lại để không đánh lừa người dùng.
  Widget _buildProjectsErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEF4444).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: Color(0xFFEF4444), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Không tải được danh sách dự án: $_projectsError',
              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
            ),
          ),
          TextButton(
            onPressed: _loadInitialData,
            child: const Text('Thử lại'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }

    final signals = _summary?.pestelSignals ?? [];
    final swotItems = _summary?.swotItems ?? [];
    final towsOptions = _summary?.towsOptions ?? [];
    final bscGoals = _summary?.bscGoals ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_projectsError != null) _buildProjectsErrorBanner(),
        // Top Toolbar (Project selector + Current Stage badge + Lenses Tabs)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: Row(
            children: [
              // Project Picker
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
                    icon: const Icon(Icons.arrow_drop_down, color: AppTheme.primary, size: 20),
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
              const SizedBox(width: 12),

              // Current Stage Badge
              StageBadge(stage: _currentStage),

              const Spacer(),

              // Sub-Tabs Header
              SizedBox(
                width: 480,
                child: TabBar(
                  controller: _tabController,
                  indicatorColor: AppTheme.primary,
                  indicatorWeight: 3,
                  labelColor: AppTheme.primary,
                  unselectedLabelColor: AppTheme.textMutedDark,
                  labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  tabs: const [
                    Tab(text: 'PESTEL Radar'),
                    Tab(text: 'SWOT Bằng Chứng'),
                    Tab(text: 'Ma Trận TOWS'),
                    Tab(text: 'BSC Scorecard'),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Tab Views Container
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              // 1. PESTEL Radar
              PestelRadarWidget(
                signals: signals,
                onCreateSignal: (dimension, title, description, impact, horizon) async {
                  if (_selectedProjectId == null) return;
                  await _lensService.createPestelSignal(
                    projectId: _selectedProjectId!,
                    dimension: dimension,
                    signalTitle: title,
                    description: description,
                    impactLevel: impact,
                    timeHorizon: horizon,
                  );
                  _loadLensData(_selectedProjectId!);
                },
                onConvertToHypothesis: (signalId) async {
                  await _lensService.convertPestelToHypothesis(signalId);
                  if (_selectedProjectId != null) _loadLensData(_selectedProjectId!);
                },
              ),

              // 2. SWOT Grid
              SwotEvidenceGridWidget(
                swotItems: swotItems,
                evidences: _evidences,
                onCreateSwotItem: (category, statement, importance, evidenceRefs) async {
                  if (_selectedProjectId == null) return;
                  await _lensService.createSwotItem(
                    projectId: _selectedProjectId!,
                    category: category,
                    statement: statement,
                    importance: importance,
                    evidenceRefs: evidenceRefs,
                  );
                  _loadLensData(_selectedProjectId!);
                },
              ),

              // 3. TOWS Matrix
              TowsMatrixWidget(
                towsOptions: towsOptions,
                onCreateOption: (quadrant, title, description) async {
                  if (_selectedProjectId == null) return;
                  await _lensService.createTowsOption(
                    projectId: _selectedProjectId!,
                    quadrant: quadrant,
                    title: title,
                    strategyDescription: description,
                  );
                  _loadLensData(_selectedProjectId!);
                },
                onConvertToTactics: (optionId, tacticTitle, weekNumber, leadIndicator) async {
                  await _lensService.convertTowsToTactics(
                    optionId: optionId,
                    tacticTitle: tacticTitle,
                    weekNumber: weekNumber,
                    leadIndicator: leadIndicator,
                  );
                  if (_selectedProjectId != null) _loadLensData(_selectedProjectId!);
                },
              ),

              // 4. BSC Scorecard
              BscScorecardWidget(
                isUnlocked: _currentStage.index >= 4,
                currentStage: _currentStage.displayNameVi,
                bscGoals: bscGoals,
                onCreateGoal: (perspective, objective, kpiName, target, current) async {
                  if (_selectedProjectId == null) return;
                  await _lensService.createBscGoal(
                    projectId: _selectedProjectId!,
                    perspective: perspective,
                    objective: objective,
                    kpiName: kpiName,
                    targetValue: target,
                    currentValue: current,
                  );
                  _loadLensData(_selectedProjectId!);
                },
              ),
            ],
          ),
        ),
      ],
    );
  }
}
