import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/localization/app_translations.dart';
import '../../../core/services/workspace_capability_manifest_controller.dart';
import '../../../core/services/workspace_capability_manifest_model.dart';
import '../../../core/widgets/surface_state_view.dart';
import 'founder_brief_models.dart';
import 'founder_trial_board_models.dart';

/// Founder Trial Board (spec §6.1). Ordered composition:
///   Start → This week → Evidence → Cash → Decision.
/// Mỗi section bọc trong [SurfaceStateView] theo `surfaceStatus` server-owned;
/// KHÔNG có agent recommendation ở R1, KHÔNG verdict.
class FounderTrialBoardView extends StatelessWidget {
  const FounderTrialBoardView({
    super.key,
    required this.board,
    required this.manifest,
    this.brief,
    this.onRetry,
    this.onConfigureFinance,
    this.onSetCycleDuration,
    this.maxCycleWeeks = 12,
  });

  final FounderTrialBoard board;
  final WorkspaceCapabilityManifestController manifest;
  final FounderBrief? brief;
  final VoidCallback? onRetry;
  final VoidCallback? onConfigureFinance;

  /// Nếu set và surface Operating Cycle cho phép thao tác, hiện chip 1..N để
  /// founder chỉnh độ dài chu kỳ (qua PATCH operating-cycle + revision).
  final void Function(int weeks)? onSetCycleDuration;
  final int maxCycleWeeks;

  Widget _section({
    required String surfaceKey,
    required String title,
    required Widget body,
  }) {
    final status = manifest.statusFor(surfaceKey);
    final surface = manifest.surfaceFor(surfaceKey);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          SurfaceStateView(
            status: status,
            surface: surface,
            onRetry: onRetry,
            onConfigure:
                surfaceKey == 'finance.cash_liquidity' ? onConfigureFinance : null,
            child: body,
          ),
        ],
      ),
    );
  }

  Widget _cycleBody() {
    final c = board.cycle;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(c.durationWeeks == null
            ? L10nKey.ftCycleUnset.tr
            : L10nKey.ftCycleSummary.trParams({
                'weeks': '${c.durationWeeks}',
                'current': '${c.currentWeek ?? 1}',
                'reviews': '${c.reviews.length}',
              })),
        if (onSetCycleDuration != null &&
            c.cycleId != null &&
            c.revision != null &&
            manifest.isInteractive('founder_trial.operating_cycle')) ...[
          const SizedBox(height: 8),
          Text(L10nKey.ftCycleDurationHint.tr, style: const TextStyle(fontSize: 12)),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            children: [
              for (var w = 1; w <= maxCycleWeeks; w++)
                ChoiceChip(
                  key: Key('cycle_week_$w'),
                  label: Text('$w'),
                  selected: c.durationWeeks == w,
                  onSelected: (_) => onSetCycleDuration!(w),
                ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _thisWeekBody() {
    final c = board.cycle;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final r in c.reviews)
          ListTile(
            dense: true,
            leading: Text('W${r.scheduledWeekNo}'),
            title: Text(r.kind),
            subtitle: Text(r.status),
          ),
        if (c.reviews.isEmpty) Text(L10nKey.ftCycleUnset.tr),
      ],
    );
  }

  Widget _evidenceBody() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(L10nKey.ftAssumptionsTitle
            .trParams({'count': '${board.focusAssumptions.length}'})),
        for (final a in board.assumptions)
          ListTile(
            dense: true,
            leading: a.isFocus ? const Icon(Icons.center_focus_strong, size: 18) : null,
            title: Text(a.statement),
            subtitle: Text('risk ${a.riskScore} • ${a.status}'),
          ),
        const Divider(),
        Text(L10nKey.ftExperimentsTitle.tr,
            style: const TextStyle(fontWeight: FontWeight.w500)),
        for (final e in board.experiments)
          ListTile(
            dense: true,
            title: Text(e.hypothesis),
            subtitle: Text('${e.method} • ${e.successCriteria}'),
            trailing: e.linkedToAssumption
                ? null
                : Tooltip(
                    message: L10nKey.ftExperimentUnlinked.tr,
                    child: const Icon(Icons.link_off, size: 16),
                  ),
          ),
        const Divider(),
        Text(L10nKey.ftEvidenceCounts.trParams({
          'approved': '${board.evidenceApproved.length}',
          'candidate': '${board.evidenceCandidate.length}',
          'rejected': '${board.evidenceRejected.length}',
        })),
        if (board.evidenceUnlinked.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              L10nKey.ftEvidenceUnlinkedNote
                  .trParams({'count': '${board.evidenceUnlinked.length}'}),
              style: const TextStyle(fontStyle: FontStyle.italic),
            ),
          ),
      ],
    );
  }

  Widget _economicsSubCard(String title, EconomicsSubcomponent? sub) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
          Text(sub?.state ?? 'UNAVAILABLE'),
          if (sub?.gap != null) Text(sub!.gap!, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  Widget _briefBody() {
    final b = brief;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (b != null) ...[
          Text(L10nKey.ftBriefTitle.tr,
              style: const TextStyle(fontWeight: FontWeight.w500)),
          for (final ax in b.axes)
            ListTile(
              dense: true,
              title: Text(ax.axis),
              subtitle: Text(ax.state +
                  (ax.knownGaps.isEmpty ? '' : ' — ${ax.knownGaps.first}')),
            ),
          const SizedBox(height: 4),
          Text(
            '${L10nKey.ftNextReviewFocus.tr}: '
            '${b.nextReviewFocus.axis ?? '—'} — ${b.nextReviewFocus.note}',
            style: const TextStyle(fontStyle: FontStyle.italic),
          ),
          const Divider(),
        ],
        for (final d in board.decisions)
          ListTile(dense: true, title: Text(d.decision), subtitle: Text(d.createdAt)),
        if (board.decisions.isEmpty) Text(L10nKey.ftDecisionsEmpty.tr),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final economics = brief?.axisFor('economics');
    return ListView(
      key: const Key('founder_trial_board'),
      padding: const EdgeInsets.all(16),
      children: [
        _section(
          surfaceKey: 'founder_trial.operating_cycle',
          title: L10nKey.ftSectionStart.tr,
          body: _cycleBody(),
        ),
        _section(
          surfaceKey: 'founder_trial.operating_cycle',
          title: L10nKey.ftSectionThisWeek.tr,
          body: _thisWeekBody(),
        ),
        _section(
          surfaceKey: 'founder_trial.evidence',
          title: L10nKey.ftSectionEvidence.tr,
          body: _evidenceBody(),
        ),
        _section(
          surfaceKey: 'finance.cash_liquidity',
          title: L10nKey.ftSectionCash.tr,
          body: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _economicsSubCard(
                  L10nKey.ftProjectBudgetTitle.tr, economics?.projectBudget),
              _economicsSubCard(L10nKey.ftWorkspaceLiquidityTitle.tr,
                  economics?.workspaceLiquidity),
              Text(L10nKey.ftWorkspaceLiquidityNote.tr,
                  style: const TextStyle(fontSize: 12)),
            ],
          ),
        ),
        _section(
          surfaceKey: 'founder_trial.founder_brief',
          title: L10nKey.ftSectionDecision.tr,
          body: _briefBody(),
        ),
        _section(
          surfaceKey: 'strategy.pestel',
          title: L10nKey.ftStrategicAnalysis.tr,
          body: const SizedBox.shrink(),
        ),
      ],
    );
  }
}

/// Tiện ích: một surface có đang cho phép thao tác ghi không.
bool surfaceIsInteractive(WorkspaceCapabilityManifestController m, String key) =>
    m.statusFor(key) == SurfaceStatus.available ||
    m.statusFor(key) == SurfaceStatus.pilot;
