import 'package:flutter/material.dart';

import '../../../core/services/workspace_capability_manifest_controller.dart';
import '../../../core/services/workspace_capability_manifest_model.dart';
import '../../../core/widgets/surface_state_view.dart';
import 'founder_trial_board_models.dart';

/// Founder Trial Board (spec §4 / §9 Slice A).
///
/// Chuỗi: Operating Cycle → Assumptions (top 1–3 focus) → Experiments →
/// Evidence (candidate/approved/rejected + unlinked) → Decisions.
/// Mỗi section bọc trong [SurfaceStateView] theo `surfaceStatus` server-owned;
/// KHÔNG có agent recommendation ở R1.
class FounderTrialBoardView extends StatelessWidget {
  const FounderTrialBoardView({
    super.key,
    required this.board,
    required this.manifest,
    this.onRetry,
    this.onConfigureFinance,
    this.onSetCycleDuration,
    this.maxCycleWeeks = 12,
  });

  final FounderTrialBoard board;
  final WorkspaceCapabilityManifestController manifest;
  final VoidCallback? onRetry;
  final VoidCallback? onConfigureFinance;
  /// Nếu set và surface Operating Cycle cho phép thao tác, hiện chip 1..N để
  /// founder chỉnh độ dài chu kỳ (gọi PUT operating-setup).
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

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('founder_trial_board'),
      padding: const EdgeInsets.all(16),
      children: [
        _section(
          surfaceKey: 'founder_trial.operating_cycle',
          title: 'Operating Cycle',
          body: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(board.cycle.durationWeeks == null
                  ? 'Chưa cấu hình chu kỳ'
                  : 'Chu kỳ ${board.cycle.durationWeeks} tuần • tuần ${board.cycle.currentWeek ?? 1}'
                      ' • ${board.cycle.reviews.length} mốc review'),
              if (onSetCycleDuration != null &&
                  manifest.isInteractive('founder_trial.operating_cycle')) ...[
                const SizedBox(height: 8),
                const Text('Độ dài chu kỳ (tuần) — 12 chỉ là gợi ý:',
                    style: TextStyle(fontSize: 12)),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 6,
                  children: [
                    for (var w = 1; w <= maxCycleWeeks; w++)
                      ChoiceChip(
                        key: Key('cycle_week_$w'),
                        label: Text('$w'),
                        selected: board.cycle.durationWeeks == w,
                        onSelected: (_) => onSetCycleDuration!(w),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
        _section(
          surfaceKey: 'founder_trial.assumptions',
          title: 'Giả thuyết (top ${board.focusAssumptions.length} cần kiểm chứng)',
          body: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final a in board.assumptions)
                ListTile(
                  dense: true,
                  leading: a.isFocus ? const Icon(Icons.center_focus_strong) : null,
                  title: Text(a.statement),
                  subtitle: Text('risk ${a.riskScore} • ${a.status}'),
                ),
            ],
          ),
        ),
        _section(
          surfaceKey: 'founder_trial.experiments',
          title: 'Experiments',
          body: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final e in board.experiments)
                ListTile(
                  dense: true,
                  title: Text(e.hypothesis),
                  subtitle: Text('${e.method} • ${e.successCriteria}'),
                  trailing: e.linkedToAssumption
                      ? null
                      : const Tooltip(
                          message: 'Chưa gắn giả thuyết',
                          child: Icon(Icons.link_off, size: 16),
                        ),
                ),
            ],
          ),
        ),
        _section(
          surfaceKey: 'founder_trial.evidence',
          title: 'Evidence',
          body: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Đã duyệt: ${board.evidenceApproved.length} • '
                  'Chờ duyệt: ${board.evidenceCandidate.length} • '
                  'Từ chối: ${board.evidenceRejected.length}'),
              if (board.evidenceUnlinked.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '${board.evidenceUnlinked.length} evidence chưa liên kết '
                    'hypothesis/experiment — không dùng để kết luận readiness.',
                    style: const TextStyle(fontStyle: FontStyle.italic),
                  ),
                ),
            ],
          ),
        ),
        _section(
          surfaceKey: 'finance.cash_liquidity',
          title: 'Workspace liquidity',
          body: const Text('Số dư/ runway ở mức workspace — không phải tiền của project.'),
        ),
        _section(
          surfaceKey: 'founder_trial.founder_brief',
          title: 'Quyết định của founder',
          body: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final d in board.decisions)
                ListTile(dense: true, title: Text(d.decision), subtitle: Text(d.createdAt)),
              if (board.decisions.isEmpty) const Text('Chưa có quyết định nào được ghi.'),
            ],
          ),
        ),
        _section(
          surfaceKey: 'strategy.pestel',
          title: 'Phân tích chiến lược sâu',
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
