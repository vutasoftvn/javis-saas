import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../core/theme/app_theme.dart';

class FundingMatchesTabContent extends StatelessWidget {
  final Map<String, dynamic> overviewData;
  final Function(int, String) onCreate12wyTask;

  const FundingMatchesTabContent({
    super.key,
    required this.overviewData,
    required this.onCreate12wyTask,
  });

  @override
  Widget build(BuildContext context) {
    final readinessAvg = (overviewData['readiness_score_avg'] as num?)?.toDouble() ?? 0.0;
    final trlCurrent = (overviewData['trl_current'] as num?)?.toInt() ?? 3;
    final companyType = overviewData['company_type'] ?? 'STARTUP';
    final projectStage = overviewData['project_stage'] ?? 'MVP';
    final topMatches = (overviewData['top_matches'] as List<dynamic>?) ?? [];
    final missingReqs = (overviewData['missing_requirements'] as List<dynamic>?) ?? [];
    final urgentAlerts = (overviewData['urgent_alerts'] as List<dynamic>?) ?? [];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (urgentAlerts.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.error.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.notification_important_rounded, color: AppTheme.error, size: 18),
                      const SizedBox(width: 8),
                      Text(
                        L10nKey.fundingAlertsTitle.tr,
                        style: const TextStyle(color: AppTheme.error, fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...urgentAlerts.map((a) => Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text('• $a', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                      )),
                ],
              ),
            ),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: _buildMetricCard(
                  title: L10nKey.fundingMetricReadiness.tr,
                  value: '${readinessAvg.toStringAsFixed(0)}/100',
                  subtitle: readinessAvg >= 70
                      ? L10nKey.fundingMetricReadinessReady.tr
                      : L10nKey.fundingMetricReadinessNeeds.tr,
                  icon: Icons.fact_check_outlined,
                  color: readinessAvg >= 70 ? AppTheme.success : AppTheme.accent,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: _buildMetricCard(
                  title: L10nKey.fundingMetricTech.tr,
                  value: 'TRL $trlCurrent',
                  subtitle: _getTrlName(trlCurrent),
                  icon: Icons.memory_rounded,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 3,
                child: _buildMetricCard(
                  title: L10nKey.fundingMetricCategory.tr,
                  value: _getCompanyTypeName(companyType.toString()),
                  subtitle: '${L10nKey.fundingMetricStageLabel.tr}: ${_getStageName(projectStage.toString())}',
                  icon: Icons.business_outlined,
                  color: AppTheme.primaryLight,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Section 1: Matched Opportunities
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                L10nKey.fundingSectionMatches.tr,
                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${topMatches.length} ${L10nKey.fundingProgramsUnit.tr}',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (topMatches.isEmpty)
            _buildEmptySection(L10nKey.fundingSectionMatchesEmpty.tr)
          else
            ...topMatches.map((m) => _buildOpportunityCard(m as Map<String, dynamic>)),

          const SizedBox(height: 24),

          // Section 2: Missing Requirements
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                L10nKey.fundingSectionMissing.tr,
                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${missingReqs.length} ${L10nKey.fundingItemsUnit.tr}',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (missingReqs.isEmpty)
            _buildEmptySection(L10nKey.fundingSectionMissingEmpty.tr)
          else
            ...missingReqs.map((r) => _buildMissingReqCard(r as Map<String, dynamic>)),

          const SizedBox(height: 24),
          _buildFundingStackCard(),
        ],
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                const SizedBox(height: 4),
                Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(subtitle, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500), maxLines: 1, overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOpportunityCard(Map<String, dynamic> match) {
    final progName = match['program_name'] ?? L10nKey.fundingProgramsFallback.tr;
    final progAuthority = match['program_authority'] ?? L10nKey.fundingAuthorityFallback.tr;
    final matchScore = ((match['match_score'] ?? 0.0) as num).toDouble();
    final readinessScore = ((match['readiness_score'] ?? 0.0) as num).toDouble();
    final eligibility = match['eligibility_status'] ?? 'POTENTIALLY_ELIGIBLE';
    final summary = match['ai_summary'] ?? '';

    Color statusColor = eligibility == 'ELIGIBLE' ? AppTheme.success : (eligibility == 'INELIGIBLE' ? AppTheme.error : AppTheme.accent);
    String statusText = eligibility == 'ELIGIBLE'
        ? L10nKey.fundingStatusEligible.tr
        : (eligibility == 'INELIGIBLE'
            ? L10nKey.fundingStatusIneligible.tr
            : L10nKey.fundingStatusPotential.tr);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(progName, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(progAuthority, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                ),
                child: Text(statusText, style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildPill('${L10nKey.fundingPillMatchScore.tr}: ${matchScore.toStringAsFixed(0)}%', AppTheme.primary),
              const SizedBox(width: 8),
              _buildPill('${L10nKey.fundingPillReadiness.tr}: ${readinessScore.toStringAsFixed(0)}%', AppTheme.primaryLight),
            ],
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ],
        ],
      ),
    );
  }

  Widget _buildMissingReqCard(Map<String, dynamic> req) {
    final title = req['title'] ?? L10nKey.fundingEvidenceFallback.tr;
    final desc = req['description'] ?? '';
    final reqId = req['id'] as int? ?? 0;
    final isResolved = req['is_resolved'] == true;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Icon(
            isResolved ? Icons.check_circle_rounded : Icons.pending_actions_rounded,
            color: isResolved ? AppTheme.success : AppTheme.accent,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                if (desc.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(desc, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                ],
              ],
            ),
          ),
          OutlinedButton.icon(
            onPressed: isResolved ? null : () => onCreate12wyTask(reqId, title),
            icon: const Icon(Icons.add_task_rounded, size: 14),
            label: Text(L10nKey.fundingAddTo12wy.tr, style: const TextStyle(fontSize: 12)),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.primary,
              side: const BorderSide(color: AppTheme.primary),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFundingStackCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppTheme.borderDark)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.pie_chart_outline_rounded, color: AppTheme.primary, size: 20),
              const SizedBox(width: 8),
              Text(
                L10nKey.fundingStackTitle.tr,
                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            L10nKey.fundingStackDesc.tr,
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildPill(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(100)),
      child: Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildEmptySection(String msg) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppTheme.borderDark)),
      child: Center(child: Text(msg, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13))),
    );
  }

  String _getCompanyTypeName(String type) => type == 'STARTUP'
      ? L10nKey.fundingCompanyStartup.tr
      : L10nKey.fundingCompanyEnterprise.tr;
  String _getStageName(String stage) => stage == 'MVP'
      ? L10nKey.fundingMvpLabel.tr
      : stage;
  String _getTrlName(int trl) => 'TRL $trl — ${Get.locale?.languageCode == 'en' ? 'Field Testing Level' : 'Mức thử nghiệm thực tế'}';
}
