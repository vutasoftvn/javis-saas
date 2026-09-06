import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/strategy_workflow_models.dart';
import '../../services/strategy_workflow_service.dart';
import '../../widgets/strategic_objective_step.dart';
import '../../widgets/bsc_focus_scope_step.dart';
import '../../widgets/strategy_analysis_step.dart';
import '../../widgets/tows_prioritization_step.dart';
import '../../../hologram_hub/widgets/lenses/bsc_scorecard_widget.dart';

/// Guided stateful sequence:
/// 1. Strategic objective
/// 2. BSC focus scope (conditional on workspace policy: off / optional / required)
/// 3. Strategy analysis (PESTEL, Resources & Capabilities with 6 approved names, SWOT with source provenance)
/// 4. TOWS evaluation and human selection (scores 1-5, counter, policy limit)
///
/// Under governed BSC workflow, BSC is NOT an independent peer tab or separate phase,
/// but a focus filter during analysis and a read-only scorecard of published OKRs.
class StrategyLensesTab extends StatefulWidget {
  final StrategyWorkflowService? workflowService;
  final WorkspaceStrategySettingsModel? initialSettings;
  final StrategicObjectiveModel? initialObjective;
  final int? initialStep;
  final List<StrategicObjectiveModel>? initialObjectives;
  final List<BscFocusScopeModel>? initialFocusScopes;
  final List<PestelSignalModel>? initialPestelSignals;
  final List<ResourceCapabilityAssessmentModel>? initialResourceAssessments;
  final List<SwotItemModel>? initialSwotItems;
  final List<TowsOptionModel>? initialTowsOptions;

  const StrategyLensesTab({
    super.key,
    this.workflowService,
    this.initialSettings,
    this.initialObjective,
    this.initialStep,
    this.initialObjectives,
    this.initialFocusScopes,
    this.initialPestelSignals,
    this.initialResourceAssessments,
    this.initialSwotItems,
    this.initialTowsOptions,
  });

  @override
  State<StrategyLensesTab> createState() => _StrategyLensesTabState();
}

class _StrategyLensesTabState extends State<StrategyLensesTab> {
  late final StrategyWorkflowService _service;

  int _currentStep = 0;
  bool _isLoading = true;
  String? _errorMessage;

  WorkspaceStrategySettingsModel? _settings;
  List<StrategicObjectiveModel> _objectives = [];
  StrategicObjectiveModel? _selectedObjective;
  List<BscFocusScopeModel> _focusScopes = [];
  List<PestelSignalModel> _pestelSignals = [];
  List<ResourceCapabilityAssessmentModel> _resourceAssessments = [];
  List<SwotItemModel> _swotItems = [];
  List<TowsOptionModel> _towsOptions = [];

  @override
  void initState() {
    super.initState();
    _service = widget.workflowService ?? StrategyWorkflowService();
    _currentStep = widget.initialStep ?? 0;
    _settings = widget.initialSettings;
    _selectedObjective = widget.initialObjective;

    if (widget.initialObjectives != null) {
      _objectives = List.from(widget.initialObjectives!);
    }
    if (widget.initialFocusScopes != null) {
      _focusScopes = List.from(widget.initialFocusScopes!);
    }
    if (widget.initialPestelSignals != null) {
      _pestelSignals = List.from(widget.initialPestelSignals!);
    }
    if (widget.initialResourceAssessments != null) {
      _resourceAssessments = List.from(widget.initialResourceAssessments!);
    }
    if (widget.initialSwotItems != null) {
      _swotItems = List.from(widget.initialSwotItems!);
    }
    if (widget.initialTowsOptions != null) {
      _towsOptions = List.from(widget.initialTowsOptions!);
    }

    if (widget.initialSettings != null && widget.initialObjectives != null) {
      _isLoading = false;
    } else {
      _loadData();
    }
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final settings = _settings ?? await _service.getWorkspaceSettings();
      final objectives = widget.initialObjectives ?? await _service.listStrategicObjectives();

      StrategicObjectiveModel? selected = _selectedObjective;
      if (selected == null && objectives.isNotEmpty) {
        selected = objectives.first;
      }

      List<BscFocusScopeModel> scopes = [];
      List<PestelSignalModel> pestel = [];
      List<ResourceCapabilityAssessmentModel> resources = [];
      List<SwotItemModel> swot = [];
      List<TowsOptionModel> tows = [];

      if (selected != null) {
        scopes = widget.initialFocusScopes ?? await _service.listFocusScopes(selected.id);
        pestel = widget.initialPestelSignals ?? await _service.listPestelSignals(selected.id);
        resources = widget.initialResourceAssessments ?? await _service.listResourceAssessments(selected.id);
        swot = widget.initialSwotItems ?? await _service.listSwotItems(selected.id);
        tows = widget.initialTowsOptions ?? await _service.listTowsOptions(selected.id);
      }

      if (mounted) {
        setState(() {
          _settings = settings;
          _objectives = objectives;
          _selectedObjective = selected;
          _focusScopes = scopes;
          _pestelSignals = pestel;
          _resourceAssessments = resources;
          _swotItems = swot;
          _towsOptions = tows;
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('[StrategyLensesTab] _loadData error: $e');
      if (mounted) {
        setState(() {
          _errorMessage = 'Không thể tải dữ liệu quy trình chiến lược: $e';
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _reloadObjectiveDetails(String objectiveId) async {
    try {
      final scopes = await _service.listFocusScopes(objectiveId);
      final pestel = await _service.listPestelSignals(objectiveId);
      final resources = await _service.listResourceAssessments(objectiveId);
      final swot = await _service.listSwotItems(objectiveId);
      final tows = await _service.listTowsOptions(objectiveId);

      if (mounted) {
        setState(() {
          _focusScopes = scopes;
          _pestelSignals = pestel;
          _resourceAssessments = resources;
          _swotItems = swot;
          _towsOptions = tows;
        });
      }
    } catch (e) {
      debugPrint('[StrategyLensesTab] _reloadObjectiveDetails error: $e');
    }
  }

  void _onObjectiveChanged(StrategicObjectiveModel? obj) {
    if (obj == null) return;
    setState(() {
      _selectedObjective = obj;
    });
    _reloadObjectiveDetails(obj.id);
  }

  void _showBscScorecardDialog() {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 30),
        child: Container(
          width: 900,
          height: 600,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFA855F7).withValues(alpha: 0.5), width: 1.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.dashboard_customize_outlined, color: Color(0xFFA855F7), size: 24),
                      SizedBox(width: 10),
                      Text(
                        'Thẻ điểm Cân bằng BSC (Scorecard chỉ xem)',
                        style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white70),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Expanded(
                child: BscScorecardWidget(
                  isUnlocked: true,
                  currentStage: 'Thực thi & Quản trị',
                  bscGoals: const [],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primaryColor));
    }

    final settings = _settings ??
        WorkspaceStrategySettingsModel(
          workspaceId: '1',
          strategyMethod: StrategyMethod.bscFilter,
          bscMode: BscMode.optional,
          maxTowsSelections: 2,
        );

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_errorMessage != null) _buildErrorBanner(),
          _buildGuidedHeader(settings),
          const SizedBox(height: 20),
          _buildStepContent(settings),
        ],
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEF4444).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: Color(0xFFEF4444), size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _errorMessage!,
              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
            ),
          ),
          TextButton(
            onPressed: _loadData,
            child: const Text('Thử lại'),
          ),
        ],
      ),
    );
  }

  Widget _buildGuidedHeader(WorkspaceStrategySettingsModel settings) {
    final steps = [
      '1. Mục tiêu chiến lược',
      settings.bscMode == BscMode.off ? '2. Trọng tâm BSC (Tắt)' : '2. Trọng tâm BSC',
      '3. Phân tích chiến lược',
      '4. Ưu tiên TOWS',
    ];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.hub_outlined, color: AppTheme.primaryColor, size: 22),
              const SizedBox(width: 10),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Quy trình Hoạch định Chiến lược (Strategy Workflow)',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Chuỗi dẫn dắt: Mục tiêu cấp cao ➔ Trọng tâm BSC ➔ Phân tích đa chiều ➔ Ma trận TOWS',
                      style: TextStyle(color: Colors.white60, fontSize: 12),
                    ),
                  ],
                ),
              ),
              OutlinedButton.icon(
                key: const Key('btn_view_bsc_scorecard'),
                onPressed: _showBscScorecardDialog,
                icon: const Icon(Icons.dashboard_customize_outlined, size: 16, color: Color(0xFFA855F7)),
                label: const Text('Thẻ điểm BSC', style: TextStyle(color: Color(0xFFA855F7), fontSize: 12)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFFA855F7)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Step indicators (Linear sequence, NOT peer tabs)
          Row(
            children: List.generate(steps.length, (idx) {
              final isActive = _currentStep == idx;
              final isCompleted = _currentStep > idx;

              return Expanded(
                child: InkWell(
                  key: Key('step_indicator_$idx'),
                  onTap: () {
                    // Can only jump to previous steps or next step if valid
                    if (idx < _currentStep || (idx == 1 && _selectedObjective != null)) {
                      setState(() => _currentStep = idx);
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
                    margin: EdgeInsets.only(right: idx < steps.length - 1 ? 8 : 0),
                    decoration: BoxDecoration(
                      color: isActive
                          ? AppTheme.primaryColor.withValues(alpha: 0.2)
                          : isCompleted
                              ? const Color(0xFF10B981).withValues(alpha: 0.15)
                              : Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: isActive
                            ? AppTheme.primaryColor
                            : isCompleted
                                ? const Color(0xFF10B981)
                                : Colors.white12,
                        width: isActive ? 1.5 : 1,
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          isCompleted
                              ? Icons.check_circle
                              : isActive
                                  ? Icons.radio_button_checked
                                  : Icons.radio_button_unchecked,
                          size: 14,
                          color: isActive
                              ? AppTheme.primaryColor
                              : isCompleted
                                  ? const Color(0xFF10B981)
                                  : Colors.white38,
                        ),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            steps[idx],
                            style: TextStyle(
                              color: isActive
                                  ? Colors.white
                                  : isCompleted
                                      ? Colors.white70
                                      : Colors.white38,
                              fontSize: 12,
                              fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildStepContent(WorkspaceStrategySettingsModel settings) {
    switch (_currentStep) {
      case 0:
        return StrategicObjectiveStep(
          objectives: _objectives,
          selectedObjective: _selectedObjective,
          onObjectiveSelected: (obj) {
            _onObjectiveChanged(obj);
          },
          onCreateObjective: (title, successDef, timeHorizon) async {
            final created = await _service.createStrategicObjective(
              title: title,
              successDefinition: successDef,
              timeHorizonEnd: timeHorizon,
            );
            setState(() {
              _objectives.insert(0, created);
              _selectedObjective = created;
            });
            await _reloadObjectiveDetails(created.id);
            return created;
          },
          onNext: () {
            setState(() => _currentStep = 1);
          },
        );

      case 1:
        if (_selectedObjective == null) {
          return const Center(child: Text('Vui lòng chọn một mục tiêu chiến lược trước.'));
        }
        return BscFocusScopeStep(
          selectedObjective: _selectedObjective!,
          settings: settings,
          focusScopes: _focusScopes,
          onSaveFocusScopes: (scopes) async {
            final updated = await _service.updateObjectiveBscFocus(
              _selectedObjective!.id,
              scopes: scopes,
            );
            setState(() {
              _focusScopes = updated;
            });
          },
          onBack: () => setState(() => _currentStep = 0),
          onNext: () => setState(() => _currentStep = 2),
        );

      case 2:
        if (_selectedObjective == null) {
          return const Center(child: Text('Vui lòng chọn một mục tiêu chiến lược trước.'));
        }
        return StrategyAnalysisStep(
          selectedObjective: _selectedObjective!,
          bscFocusScopes: _focusScopes,
          pestelSignals: _pestelSignals,
          resourceAssessments: _resourceAssessments,
          swotItems: _swotItems,
          onCreatePestelSignal: ({
            required dimension,
            required statement,
            required impact,
            required certainty,
            evidenceRefs,
            bscPerspectives,
          }) async {
            final created = await _service.createPestelSignal(
              objectiveId: _selectedObjective!.id,
              dimension: dimension,
              statement: statement,
              impact: impact,
              certainty: certainty,
              evidenceRefs: evidenceRefs,
              bscPerspectives: bscPerspectives,
            );
            setState(() => _pestelSignals.add(created));
          },
          onCreateResourceAssessment: ({
            required category,
            required statement,
            required strengthLevel,
            evidenceRefs,
            bscPerspectives,
          }) async {
            final created = await _service.createResourceAssessment(
              objectiveId: _selectedObjective!.id,
              category: category,
              statement: statement,
              strengthLevel: strengthLevel,
              evidenceRefs: evidenceRefs,
              bscPerspectives: bscPerspectives,
            );
            setState(() => _resourceAssessments.add(created));
          },
          onCreateSwotItem: ({
            required itemType,
            required content,
            required sourceType,
            sourceId,
            evidenceRefs,
            bscPerspectives,
          }) async {
            final created = await _service.createSwotItem(
              objectiveId: _selectedObjective!.id,
              kind: itemType,
              statement: content,
              sourceType: sourceType,
              sourceId: sourceId,
              evidenceRefs: evidenceRefs,
              bscPerspectives: bscPerspectives,
            );
            setState(() => _swotItems.add(created));
          },
          onDeriveSwotDrafts: () async {
            final drafts = await _service.deriveSwotDrafts(_selectedObjective!.id);
            setState(() => _swotItems.addAll(drafts));
          },
          onBack: () => setState(() => _currentStep = 1),
          onNext: () => setState(() => _currentStep = 3),
        );

      case 3:
      default:
        if (_selectedObjective == null) {
          return const Center(child: Text('Vui lòng chọn một mục tiêu chiến lược trước.'));
        }
        return TowsPrioritizationStep(
          selectedObjective: _selectedObjective!,
          bscFocusScopes: _focusScopes,
          towsOptions: _towsOptions,
          selectionLimit: settings.maxTowsSelections,
          onCreateOption: ({
            required optionType,
            required title,
            description,
            swotLinkIds,
          }) async {
            final created = await _service.createTowsOption(
              objectiveId: _selectedObjective!.id,
              towsType: optionType,
              title: title,
              description: description,
              swotLinkIds: swotLinkIds,
            );
            setState(() => _towsOptions.add(created));
          },
          onEvaluateOption: (optionId, {required impactScore, required difficultyScore, rationale}) async {
            final updated = await _service.evaluateTowsOption(
              optionId,
              impactScore: impactScore,
              difficultyScore: difficultyScore,
              evaluationNotes: rationale,
            );
            final idx = _towsOptions.indexWhere((o) => o.id == optionId);
            if (idx != -1) {
              setState(() => _towsOptions[idx] = updated);
            }
          },
          onSelectOption: (optionId, {required selectionRationale}) async {
            final updated = await _service.selectTowsOption(
              optionId,
              selectionRationale: selectionRationale,
            );
            final idx = _towsOptions.indexWhere((o) => o.id == optionId);
            if (idx != -1) {
              setState(() => _towsOptions[idx] = updated);
            }
          },
          onRejectOption: (optionId, {required rejectionReason}) async {
            final updated = await _service.rejectTowsOption(
              optionId,
              rejectionReason: rejectionReason,
            );
            final idx = _towsOptions.indexWhere((o) => o.id == optionId);
            if (idx != -1) {
              setState(() => _towsOptions[idx] = updated);
            }
          },
          onBack: () => setState(() => _currentStep = 2),
        );
    }
  }
}
