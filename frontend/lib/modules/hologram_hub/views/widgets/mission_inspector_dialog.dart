import 'package:flutter/material.dart';

class MissionInspectorDialog extends StatelessWidget {
  final Map<String, dynamic> mission;

  const MissionInspectorDialog({
    super.key,
    required this.mission,
  });

  static void show(BuildContext context, Map<String, dynamic> mission) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (context) => MissionInspectorDialog(mission: mission),
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = mission['title']?.toString() ?? 'Chi tiết nhiệm vụ';
    final missionId = mission['mission_id']?.toString() ?? '';
    final agent = mission['agent']?.toString() ?? 'AI Specialist';
    final status = (mission['status']?.toString() ?? 'running').toUpperCase();
    final progress = (mission['progress_percent'] as num?)?.toInt() ?? 50;
    final currentStep = mission['current_step']?.toString() ?? 'Đang thực thi';
    final nextStep = mission['next_step']?.toString() ?? '';
    final budget = mission['budget'] as Map<String, dynamic>? ?? {};
    final loopHealth = mission['loop_health'] as Map<String, dynamic>? ?? {};
    final verificationStatus = mission['verification_status']?.toString() ?? 'UNKNOWN';
    final verificationDetail = mission['verification_detail'] as Map<String, dynamic>? ?? {};
    final timeline = mission['timeline'] as List<dynamic>? ?? [];
    final toolCalls = mission['tool_calls'] as List<dynamic>? ?? [];
    final evidence = mission['evidence'] as List<dynamic>? ?? [];
    final runtimeSessions = mission['runtime_sessions'] as List<dynamic>? ?? [];
    final resumeStatus = mission['resume_status']?.toString();


    return Dialog(
      backgroundColor: const Color(0xFF090E1B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Container(
        width: 860,
        height: 720,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Top Header ──────────────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.3),
                    ),
                  ),
                  child: const Icon(
                    Icons.radar_rounded,
                    color: Color(0xFF00E5FF),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 8),
                          _buildStatusBadge(status),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Text(
                            'ID: $missionId',
                            style: const TextStyle(
                              color: Color(0xFF64748B),
                              fontSize: 12,
                              fontFamily: 'monospace',
                            ),
                          ),
                          const SizedBox(width: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF10B981).withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.smart_toy_outlined,
                                  size: 12,
                                  color: Color(0xFF34D399),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  agent,
                                  style: const TextStyle(
                                    color: Color(0xFF34D399),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close_rounded, color: Color(0xFF94A3B8)),
                  splashRadius: 20,
                ),
              ],
            ),
            const SizedBox(height: 20),

            // ── 3 Key Metrics Cards: Budget, Loop Health, Reality Verification ──
            Row(
              children: [
                Expanded(
                  child: _buildMetricCard(
                    icon: Icons.account_balance_wallet_outlined,
                    iconColor: const Color(0xFF38BDF8),
                    title: 'NGÂN SÁCH (BUDGET)',
                    value: '\$${(budget['current_cost_usd'] as num?)?.toStringAsFixed(2) ?? '0.00'} / \$${(budget['max_cost_usd'] as num?)?.toStringAsFixed(2) ?? '1.00'}',
                    subtitle: 'Giới hạn: ${budget['max_steps'] ?? 10} bước • ${(budget['budget_status'] == 'exceeded') ? 'VƯỢT' : 'ỔN ĐỊNH'}',
                    badgeColor: (budget['budget_status'] == 'exceeded') ? Colors.redAccent : const Color(0xFF38BDF8),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricCard(
                    icon: Icons.all_inclusive_rounded,
                    iconColor: (loopHealth['status'] == 'stuck') ? Colors.redAccent : const Color(0xFF10B981),
                    title: 'SỨC KHỎE VÒNG LẶP',
                    value: (loopHealth['status'] == 'stuck') ? 'CẢNH BÁO LẶP' : 'KHỎE MẠNH (100%)',
                    subtitle: (loopHealth['status'] == 'stuck') ? 'Phát hiện lặp tool' : 'Không có lặp vô hạn',
                    badgeColor: (loopHealth['status'] == 'stuck') ? Colors.redAccent : const Color(0xFF10B981),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricCard(
                    icon: Icons.verified_user_outlined,
                    iconColor: _getVerificationColor(verificationStatus),
                    title: 'KIỂM CHỨNG THỰC TẾ',
                    value: verificationStatus,
                    subtitle: '${evidence.length} bằng chứng • DB Check',
                    badgeColor: _getVerificationColor(verificationStatus),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // ── Progress Bar ─────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF131D35),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Tiến độ thực hiện: $currentStep',
                        style: const TextStyle(
                          color: Color(0xFFE2E8F0),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '$progress%',
                        style: const TextStyle(
                          color: Color(0xFF34D399),
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress / 100.0,
                      minHeight: 6,
                      backgroundColor: const Color(0xFF1E293B),
                      valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF10B981)),
                    ),
                  ),
                  if (nextStep.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Tiếp theo: $nextStep',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 11),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            if (resumeStatus == 'awaiting_specialist_resume') ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.35)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.hourglass_top_rounded, size: 14, color: Color(0xFFFBBF24)),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Đang chờ specialist hoàn tất để tiếp tục nhiệm vụ',
                        style: TextStyle(color: Color(0xFFFBBF24), fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // ── Tab Content: Timeline, Tool Calls, Evidence, Runtime Sessions ──
            Expanded(
              child: DefaultTabController(
                length: 4,
                child: Column(
                  children: [
                    Container(
                      height: 36,
                      decoration: BoxDecoration(
                        color: const Color(0xFF10192E),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: TabBar(
                        indicator: BoxDecoration(
                          color: const Color(0xFF00E5FF).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF00E5FF).withValues(alpha: 0.5)),
                        ),
                        labelColor: const Color(0xFF00E5FF),
                        unselectedLabelColor: const Color(0xFF94A3B8),
                        labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                        tabs: [
                          Tab(text: 'Dòng thời gian (${timeline.length})'),
                          Tab(text: 'Tool Calls (${toolCalls.length})'),
                          Tab(text: 'Bằng chứng & Chứng chỉ (${evidence.length})'),
                          Tab(text: 'Runtime Sessions (${runtimeSessions.length})'),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: TabBarView(
                        children: [
                          _buildTimelineView(timeline),
                          _buildToolCallsView(toolCalls),
                          _buildEvidenceView(evidence, verificationDetail),
                          _buildRuntimeSessionsView(runtimeSessions),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String value,
    required String subtitle,
    required Color badgeColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: iconColor),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: badgeColor,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              fontFamily: 'monospace',
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color bg = const Color(0xFF10B981).withValues(alpha: 0.15);
    Color fg = const Color(0xFF34D399);

    if (status.contains('WAIT') || status.contains('APPROVAL')) {
      bg = const Color(0xFFF59E0B).withValues(alpha: 0.15);
      fg = const Color(0xFFFBBF24);
    } else if (status.contains('FAIL') || status.contains('CANCEL')) {
      bg = const Color(0xFFEF4444).withValues(alpha: 0.15);
      fg = const Color(0xFFF87171);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: fg.withValues(alpha: 0.4)),
      ),
      child: Text(
        status,
        style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.w700),
      ),
    );
  }

  Color _getVerificationColor(String status) {
    switch (status.toUpperCase()) {
      case 'VERIFIED':
        return const Color(0xFF10B981);
      case 'PARTIAL':
        return const Color(0xFFF59E0B);
      case 'FAILED':
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF64748B);
    }
  }

  Widget _buildTimelineView(List<dynamic> timeline) {
    if (timeline.isEmpty) {
      return _buildEmptyState('Chưa có sự kiện nào trong dòng thời gian.');
    }

    return ListView.separated(
      itemCount: timeline.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final item = timeline[index] as Map<String, dynamic>;
        final eventType = item['event_type']?.toString() ?? 'event';
        final actor = item['actor']?.toString() ?? 'system';
        final ts = item['timestamp']?.toString() ?? '';

        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF10192E),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFF00E5FF),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      eventType.replaceAll('_', ' ').toUpperCase(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Tác tử: $actor • $ts',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildToolCallsView(List<dynamic> toolCalls) {
    if (toolCalls.isEmpty) {
      return _buildEmptyState('Chưa có lệnh gọi Tool nào được ghi nhận.');
    }

    return ListView.separated(
      itemCount: toolCalls.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final tc = toolCalls[index] as Map<String, dynamic>;
        final toolName = tc['tool_name']?.toString() ?? 'tool';
        final status = tc['status']?.toString() ?? 'success';
        final risk = tc['risk_level']?.toString() ?? 'low';

        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF10192E),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            children: [
              const Icon(Icons.build_circle_outlined, size: 16, color: Color(0xFF38BDF8)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      toolName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        fontFamily: 'monospace',
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Rủi ro: $risk • Trạng thái: $status',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEvidenceView(List<dynamic> evidence, Map<String, dynamic> certDetail) {
    if (evidence.isEmpty && certDetail.isEmpty) {
      return _buildEmptyState('Chưa có bằng chứng (Artifact) hay chứng chỉ kiểm định nào.');
    }

    return ListView(
      children: [
        if (certDetail.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF10192E),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.workspace_premium_outlined, color: Color(0xFF34D399), size: 16),
                    SizedBox(width: 6),
                    Text(
                      'CHỨNG CHỈ KIỂM CHỨNG (OUTCOME CERTIFICATE)',
                      style: TextStyle(
                        color: Color(0xFF34D399),
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Kết luận: ${certDetail['verdict'] ?? 'N/A'}',
                  style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                ),
                if (certDetail['evidence'] != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Bằng chứng xác thực: ${(certDetail['evidence'] as List).join(', ')}',
                    style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
        ...evidence.map((ev) {
          final item = ev as Map<String, dynamic>;
          final title = item['title']?.toString() ?? 'Bằng chứng';
          final type = item['type']?.toString() ?? 'artifact';

          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF10192E),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              children: [
                const Icon(Icons.attachment_rounded, size: 16, color: Color(0xFFF59E0B)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Loại: $type',
                        style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }

  Widget _buildRuntimeSessionsView(List<dynamic> runtimeSessions) {
    if (runtimeSessions.isEmpty) {
      return _buildEmptyState('Chưa có Runtime Session nào được ghi nhận.');
    }

    return ListView.separated(
      itemCount: runtimeSessions.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final rs = runtimeSessions[index] as Map<String, dynamic>;
        final runtimeType = rs['runtime_type']?.toString() ?? 'UNKNOWN';
        final externalId = rs['external_session_id']?.toString() ?? '—';
        final status = rs['status']?.toString() ?? 'active';
        final finishedAt = rs['finished_at']?.toString();

        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF10192E),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF8B5CF6).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  runtimeType,
                  style: const TextStyle(color: Color(0xFFA78BFA), fontSize: 11, fontWeight: FontWeight.w700),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      externalId,
                      style: const TextStyle(color: Colors.white, fontSize: 12, fontFamily: 'monospace'),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      finishedAt != null ? 'Trạng thái: $status • Kết thúc: $finishedAt' : 'Trạng thái: $status',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEmptyState(String msg) {

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.inbox_outlined, size: 28, color: Color(0xFF475569)),
          const SizedBox(height: 8),
          Text(msg, style: const TextStyle(color: Color(0xFF64748B), fontSize: 12)),
        ],
      ),
    );
  }
}
