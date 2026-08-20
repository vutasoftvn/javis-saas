import 'package:flutter/material.dart';
import '../../../data/models/validation_models.dart';
import '../../../modules/strategy/services/validation_service.dart';

class ProjectValidationCard extends StatefulWidget {
  final int projectId;
  final String projectName;
  final VoidCallback onOpenStudio;
  final VoidCallback onContinueInterview;
  final VoidCallback onMakeDecision;

  const ProjectValidationCard({
    super.key,
    required this.projectId,
    this.projectName = 'COSA Hospitality',
    required this.onOpenStudio,
    required this.onContinueInterview,
    required this.onMakeDecision,
  });

  @override
  State<ProjectValidationCard> createState() => _ProjectValidationCardState();
}

class _ProjectValidationCardState extends State<ProjectValidationCard> {
  StateVectorModel? _stateVector;
  RiskMatrixModel? _riskMatrix;
  ValidationReviewModel? _latestReview;
  NextBestActionDetailModel? _nextBestAction;
  ProblemScorecardModel? _scorecard;
  RoleCoverageModel? _roleCoverage;
  SolutionBiasRiskModel? _solutionBias;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadValidationSummary();
  }

  Future<void> _loadValidationSummary() async {
    setState(() => _isLoading = true);
    try {
      final sv = await ValidationService.getStateVector(widget.projectId);
      final rm = await ValidationService.getRiskMatrix(widget.projectId);
      final nba = await ValidationService.getNextBestAction(widget.projectId);
      final review = await ValidationService.getLatestReview(widget.projectId);
      final sc = await ValidationService.getProblemScorecard(widget.projectId);
      final rc = await ValidationService.getRoleCoverage(widget.projectId);
      final sb = await ValidationService.getSolutionBiasRisk(widget.projectId);

      if (mounted) {
        setState(() {
          _stateVector = sv;
          _riskMatrix = rm;
          _nextBestAction = nba;
          _latestReview = review;
          _scorecard = sc;
          _roleCoverage = rc;
          _solutionBias = sb;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    if (_isLoading) {
      return Container(
        height: 240,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E222D) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: isDark ? const Color(0xFF2A3142) : const Color(0xFFE2E8F0)),
        ),
        child: const Center(child: CircularProgressIndicator()),
      );
    }

    final sv = _stateVector;
    final critRisks = _riskMatrix?.criticalRisks ?? [];
    final topCrit = critRisks.isNotEmpty ? critRisks.first : null;
    final verdict = _latestReview?.verdict ?? 'TEST MORE';
    final confPct = ((sv?.overallConfidence ?? 0.58) * 100).toInt();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E222D) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? const Color(0xFF2A3142) : const Color(0xFFE2E8F0),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Header: Title & Stage
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.blueAccent.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.verified_outlined, color: Colors.blueAccent, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'PROJECT VALIDATION',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 0.8, color: Colors.blueAccent),
                      ),
                      Text(
                        widget.projectName,
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.purpleAccent.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.purpleAccent.withValues(alpha: 0.4)),
                ),
                child: Text(
                  sv?.projectStage ?? 'VALIDATION',
                  style: const TextStyle(color: Colors.purpleAccent, fontWeight: FontWeight.bold, fontSize: 11),
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),
          const Divider(height: 1),
          const SizedBox(height: 16),

          // 2. Confidence & Mini State Vector Bars
          Row(
            children: [
              Text('Confidence: $confPct%', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
              const SizedBox(width: 12),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (sv?.overallConfidence ?? 0.58),
                    minHeight: 6,
                    backgroundColor: isDark ? const Color(0xFF2A3142) : Colors.grey.shade200,
                    color: Colors.cyanAccent.shade700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // 5 Dimensions Mini Bars
          _buildMiniDimensionRow('Customer', 0.82, Colors.green),
          const SizedBox(height: 6),
          _buildMiniDimensionRow('Problem', 0.74, Colors.greenAccent),
          const SizedBox(height: 6),
          _buildMiniDimensionRow('Solution', 0.51, Colors.amber),
          const SizedBox(height: 6),
          _buildMiniDimensionRow('Pricing', 0.22, Colors.redAccent),
          const SizedBox(height: 6),
          _buildMiniDimensionRow('Channel', 0.35, Colors.orangeAccent),

          const SizedBox(height: 16),

          // 3. Critical Assumption Callout
          if (topCrit != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.redAccent.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.redAccent.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Critical Assumption (${topCrit.riskScore}/25 Risk)',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.redAccent)),
                        const SizedBox(height: 2),
                        Text(topCrit.statement, style: const TextStyle(fontSize: 13)),
                      ],
                    ),
                  ),
                ],
              ),
            ),

          const SizedBox(height: 12),

          // F2 & F3: Solution Bias Warning Banner (If Risk detected)
          if (_solutionBias != null && _solutionBias!.solutionBiasRisk == 'HIGH')
            Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.amber.withValues(alpha: 0.4)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _solutionBias!.warningTitle ?? '⚠ SOLUTION BIAS RISK',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.amber),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _solutionBias!.warningMessage ?? 'Solution detail cao nhưng Problem evidence chưa đủ.',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

          // F2 & F3: Problem Severity Scorecard & Role Coverage Matrix
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF181B22) : const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: isDark ? const Color(0xFF2A3142) : const Color(0xFFE2E8F0)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.analytics_outlined, size: 16, color: Colors.cyanAccent),
                        SizedBox(width: 6),
                        Text('Problem-First Intelligence', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: ((_scorecard?.totalScore ?? 25) >= 40 ? Colors.green : Colors.orangeAccent).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'Pain: ${_scorecard?.totalScore ?? 25}/50 (Heuristic: 40)',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: (_scorecard?.totalScore ?? 25) >= 40 ? Colors.greenAccent : Colors.orangeAccent,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Text('Role Coverage: ', style: TextStyle(fontSize: 11, color: Colors.grey)),
                    _buildRoleChip('User (${_roleCoverage?.userCount ?? 0})', (_roleCoverage?.userCount ?? 0) > 0),
                    const SizedBox(width: 4),
                    _buildRoleChip('Buyer (${_roleCoverage?.buyerCount ?? 0})', (_roleCoverage?.buyerCount ?? 0) > 0),
                    const SizedBox(width: 4),
                    _buildRoleChip(
                      'Decider (${_roleCoverage?.decisionMakerCount ?? 0})',
                      (_roleCoverage?.decisionMakerCount ?? 0) > 0,
                      isWarning: (_roleCoverage?.hasDecisionMakerGap ?? false),
                    ),
                    const SizedBox(width: 4),
                    _buildRoleChip('Influencer (${_roleCoverage?.influencerCount ?? 0})', (_roleCoverage?.influencerCount ?? 0) > 0),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 14),

          // 4. AI Recommendation & NBA
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('AI Recommendation:', style: TextStyle(fontSize: 13, color: Colors.grey)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.blue.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(verdict, style: const TextStyle(color: Colors.blueAccent, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.amber.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.next_plan_outlined, color: Colors.amber, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Next Best Action', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.amber)),
                      const SizedBox(height: 2),
                      Text(_nextBestAction?.title ?? 'Test pricing before building more features.',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                      if (_nextBestAction?.why != null)
                        Text(_nextBestAction!.why, style: const TextStyle(fontSize: 11, color: Colors.grey)),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // 5. Quick Action Buttons Bar
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ElevatedButton.icon(
                onPressed: widget.onOpenStudio,
                icon: const Icon(Icons.dashboard_customize_outlined, size: 16),
                label: const Text('Mở Studio'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blueAccent,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
              ),
              OutlinedButton.icon(
                onPressed: widget.onContinueInterview,
                icon: const Icon(Icons.chat_bubble_outline, size: 16),
                label: const Text('Phỏng Vấn Tiếp'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
              ),
              OutlinedButton.icon(
                onPressed: widget.onMakeDecision,
                icon: const Icon(Icons.how_to_reg_outlined, size: 16),
                label: const Text('Ra Quyết Định'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.greenAccent.shade400,
                  side: BorderSide(color: Colors.greenAccent.shade400),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMiniDimensionRow(String name, double val, Color color) {
    return Row(
      children: [
        SizedBox(
          width: 65,
          child: Text(name, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: val,
              minHeight: 5,
              backgroundColor: Colors.grey.withValues(alpha: 0.15),
              color: color,
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 32,
          child: Text('${(val * 100).toInt()}%',
              textAlign: TextAlign.right,
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color)),
        ),
      ],
    );
  }

  Widget _buildRoleChip(String label, bool isCovered, {bool isWarning = false}) {
    Color chipColor = isCovered
        ? Colors.greenAccent.shade400
        : (isWarning ? Colors.amberAccent : Colors.grey.shade600);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: chipColor.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: chipColor.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isCovered
                ? Icons.check
                : (isWarning ? Icons.warning_amber_rounded : Icons.remove),
            size: 10,
            color: chipColor,
          ),
          const SizedBox(width: 2),
          Text(label, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: chipColor)),
        ],
      ),
    );
  }
}
