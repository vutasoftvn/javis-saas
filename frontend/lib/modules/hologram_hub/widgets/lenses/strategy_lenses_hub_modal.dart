import 'package:flutter/material.dart';
import '../../../../data/models/stage_model.dart';
import '../../../../data/models/strategy_lens_model.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../shared/widgets/stage_badge.dart';
import 'pestel_radar_widget.dart';
import 'swot_evidence_grid_widget.dart';
import 'tows_matrix_widget.dart';
import 'bsc_scorecard_widget.dart';

class StrategyLensesHubModal extends StatefulWidget {
  final int projectId;
  final ProjectStage currentStage;
  final StageLensSummaryModel? summary;
  final List<EvidenceModel> evidences;
  final Function(PestelDimension dimension, String title, String desc, String impact, String horizon) onCreatePestelSignal;
  final Function(int signalId) onConvertPestelToHypothesis;
  final Function(SwotType category, String statement, double importance, List<int> evidenceRefs) onCreateSwotItem;
  final Function(TowsType quadrant, String title, String description) onCreateTowsOption;
  final Function(int optionId, String tacticTitle, int weekNumber, String leadIndicator) onConvertTowsToTactics;
  final Function(BscPerspective perspective, String objective, String kpiName, String target, String current) onCreateBscGoal;

  const StrategyLensesHubModal({
    super.key,
    required this.projectId,
    required this.currentStage,
    required this.summary,
    this.evidences = const [],
    required this.onCreatePestelSignal,
    required this.onConvertPestelToHypothesis,
    required this.onCreateSwotItem,
    required this.onCreateTowsOption,
    required this.onConvertTowsToTactics,
    required this.onCreateBscGoal,
  });

  static void show(
    BuildContext context, {
    required int projectId,
    required ProjectStage currentStage,
    required StageLensSummaryModel? summary,
    List<EvidenceModel> evidences = const [],
    required Function(PestelDimension dimension, String title, String desc, String impact, String horizon) onCreatePestelSignal,
    required Function(int signalId) onConvertPestelToHypothesis,
    required Function(SwotType category, String statement, double importance, List<int> evidenceRefs) onCreateSwotItem,
    required Function(TowsType quadrant, String title, String description) onCreateTowsOption,
    required Function(int optionId, String tacticTitle, int weekNumber, String leadIndicator) onConvertTowsToTactics,
    required Function(BscPerspective perspective, String objective, String kpiName, String target, String current) onCreateBscGoal,
  }) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 30),
        child: StrategyLensesHubModal(
          projectId: projectId,
          currentStage: currentStage,
          summary: summary,
          evidences: evidences,
          onCreatePestelSignal: onCreatePestelSignal,
          onConvertPestelToHypothesis: onConvertPestelToHypothesis,
          onCreateSwotItem: onCreateSwotItem,
          onCreateTowsOption: onCreateTowsOption,
          onConvertTowsToTactics: onConvertTowsToTactics,
          onCreateBscGoal: onCreateBscGoal,
        ),
      ),
    );
  }

  @override
  State<StrategyLensesHubModal> createState() => _StrategyLensesHubModalState();
}

class _StrategyLensesHubModalState extends State<StrategyLensesHubModal>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final summary = widget.summary;
    final pestelSignals = summary?.pestelSignals ?? [];
    final swotItems = summary?.swotItems ?? [];
    final towsOptions = summary?.towsOptions ?? [];
    final bscGoals = summary?.bscGoals ?? [];
    final isBscUnlocked = summary?.isBscUnlocked ?? (widget.currentStage == ProjectStage.s5OperateGrowth || widget.currentStage == ProjectStage.s6ScaleGovern);

    return Container(
      width: 1080,
      height: 720,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: widget.currentStage.primaryColor.withValues(alpha: 0.5), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.6),
            blurRadius: 30,
            spreadRadius: 5,
          ),
        ],
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B).withValues(alpha: 0.7),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
              border: const Border(bottom: BorderSide(color: Colors.white12)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: widget.currentStage.primaryColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.lens_blur_outlined, color: widget.currentStage.primaryColor, size: 22),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Khung 4 Lăng Kính Chiến Lược (Strategy Lenses Hub)',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Phân tích định hướng chuẩn COSA: PESTEL -> SWOT -> TOWS -> Balanced Scorecard',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12),
                    ),
                  ],
                ),
                const Spacer(),
                StageBadge(stage: widget.currentStage, showFullName: true),
                const SizedBox(width: 12),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          // Tabs
          Container(
            decoration: const BoxDecoration(
              color: Color(0xFF1E293B),
              border: Border(bottom: BorderSide(color: Colors.white12)),
            ),
            child: TabBar(
              controller: _tabController,
              indicatorColor: widget.currentStage.primaryColor,
              indicatorWeight: 3,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.white60,
              labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
              tabs: [
                Tab(
                  icon: const Icon(Icons.radar_outlined, size: 18),
                  text: 'PESTEL Radar (${pestelSignals.length})',
                ),
                Tab(
                  icon: const Icon(Icons.grid_view_outlined, size: 18),
                  text: 'SWOT Có Bằng Chứng (${swotItems.length})',
                ),
                Tab(
                  icon: const Icon(Icons.alt_route_outlined, size: 18),
                  text: 'TOWS & 12WY Tactics (${towsOptions.length})',
                ),
                Tab(
                  icon: Icon(isBscUnlocked ? Icons.dashboard_outlined : Icons.lock_outline, size: 18),
                  text: isBscUnlocked ? 'Balanced Scorecard (${bscGoals.length})' : 'Balanced Scorecard (Khóa)',
                ),
              ],
            ),
          ),

          // Content Views
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: TabBarView(
                controller: _tabController,
                children: [
                  PestelRadarWidget(
                    signals: pestelSignals,
                    onCreateSignal: widget.onCreatePestelSignal,
                    onConvertToHypothesis: widget.onConvertPestelToHypothesis,
                  ),
                  SwotEvidenceGridWidget(
                    swotItems: swotItems,
                    evidences: widget.evidences,
                    onCreateSwotItem: widget.onCreateSwotItem,
                  ),
                  TowsMatrixWidget(
                    towsOptions: towsOptions,
                    onCreateOption: widget.onCreateTowsOption,
                    onConvertToTactics: widget.onConvertTowsToTactics,
                  ),
                  BscScorecardWidget(
                    isUnlocked: isBscUnlocked,
                    currentStage: widget.currentStage.shortNameVi,
                    bscGoals: bscGoals,
                    onCreateGoal: widget.onCreateBscGoal,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
