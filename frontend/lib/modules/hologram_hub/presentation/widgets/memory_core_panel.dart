import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'audio_waveform_painter.dart';
import 'hud_card.dart';

class MemoryCorePanel extends StatefulWidget {
  final Map<String, dynamic>? data;
  final VoidCallback? onViewAgents;
  final double gap;

  const MemoryCorePanel({
    super.key,
    this.data,
    this.onViewAgents,
    this.gap = 24,
  });

  @override
  State<MemoryCorePanel> createState() => _MemoryCorePanelState();
}

class _MemoryCorePanelState extends State<MemoryCorePanel>
    with TickerProviderStateMixin {
  late AnimationController _graphController;
  late AnimationController _neuralController;

  @override
  void initState() {
    super.initState();
    _graphController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();

    _neuralController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
  }

  @override
  void dispose() {
    _graphController.dispose();
    _neuralController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final memData = widget.data?['memory_core'] as Map<String, dynamic>?;
    final agentsData = widget.data?['active_agents'] as Map<String, dynamic>?;
    final agentsList = (agentsData?['items'] as List<dynamic>?) ?? [];
    final buildMode = widget.data?['build_mode'] as Map<String, dynamic>?;
    final buildTelemetryAvailable = (buildMode?['available'] as bool?) ?? false;

    return Column(
      mainAxisSize: MainAxisSize.max,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 1. MEMORY CORE CARD
        Expanded(
          child: hudCard(
            onTap: widget.onViewAgents,
            padding: const EdgeInsets.all(10),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  hudCardHeader(
                    title: 'BỘ NHỚ TRUNG TÂM',
                    badgeText: 'CHỜ ◇',
                    badgeColor: const Color(0xFF38BDF8),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Left stats
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildStatRow(
                              'TỔNG BỘ NHỚ',
                              '${memData?['total_memories'] ?? 0}',
                            ),
                            const SizedBox(height: 6),
                            _buildStatRow(
                              'NÚT TRI THỨC',
                              '${memData?['knowledge_nodes'] ?? 0}',
                            ),
                            const SizedBox(height: 6),
                            _buildStatRow(
                              'LIÊN KẾT',
                              '${memData?['connections'] ?? 0}',
                            ),
                          ],
                        ),
                      ),

                      // Right constellation graph
                      SizedBox(
                        width: 75,
                        height: 75,
                        child: AnimatedBuilder(
                          animation: _graphController,
                          builder: (context, child) {
                            return CustomPaint(
                              painter: _ConstellationGraphPainter(
                                phase: _graphController.value,
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),

        SizedBox(height: widget.gap),

        // 2. ACTIVE AGENTS CARD
        Expanded(
          child: hudCard(
            onTap: widget.onViewAgents,
            padding: const EdgeInsets.all(10),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  hudCardHeader(
                    title: 'AGENT HOẠT ĐỘNG',
                    badgeText: 'TRỰC TIẾP ${agentsList.length}',
                    badgeColor: const Color(0xFF10B981),
                  ),
                  const SizedBox(height: 10),
                  ...agentsList.take(5).map((agent) {
                    final name = agent['name'] as String? ?? 'Agent';
                    final rawStatus = agent['status'] as String? ?? 'Running';
                    final status = rawStatus == 'Running'
                        ? 'Đang chạy'
                        : rawStatus;
                    final iconColor = _getAgentColor(name);

                    return Padding(
                      padding: const EdgeInsets.only(bottom: 7.0),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: iconColor.withValues(alpha: 0.15),
                            ),
                            child: Icon(
                              Icons.smart_toy_outlined,
                              size: 13,
                              color: iconColor,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              name,
                              style: const TextStyle(
                                color: Color(0xFFCBD5E1),
                                fontSize: 14,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            status,
                            style: const TextStyle(
                              color: Color(0xFF38BDF8),
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
        ),

        SizedBox(height: widget.gap),

        // 3. BUILD MODE CARD
        Expanded(
          child: hudCard(
            padding: const EdgeInsets.all(10),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  hudCardHeader(
                    title: 'CHẾ ĐỘ PHÁT TRIỂN',
                    badgeText: buildTelemetryAvailable
                        ? 'ĐÃ BẬT'
                        : 'CHẾ ĐỘ CLOUD',
                    badgeColor: buildTelemetryAvailable
                        ? const Color(0xFF10B981)
                        : const Color(0xFF64748B),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'HOẠT ĐỘNG THẦN KINH',
                        style: TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        ((buildMode?['neural_activity'] as String?) ==
                                    'REAL-TIME' ||
                                buildMode?['neural_activity'] == null)
                            ? 'THỜI GIAN THỰC'
                            : (buildMode!['neural_activity'] as String),
                        style: const TextStyle(
                          color: Color(0xFF10B981),
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  AnimatedBuilder(
                    animation: _neuralController,
                    builder: (context, child) {
                      return SizedBox(
                        height: 22,
                        child: CustomPaint(
                          painter: AudioWaveformPainter(
                            animationValue: _neuralController.value,
                            isOscilloscope: true,
                            primaryColor: const Color(0xFF00F0FF),
                            secondaryColor: const Color(0xFF3B82F6),
                          ),
                        ),
                      );
                    },
                  ),
                  if (buildTelemetryAvailable) ...[
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'MỨC DÙNG CPU',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          '${buildMode?['cpu_usage'] ?? 0}%',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value: ((buildMode?['cpu_usage'] ?? 0) as num) / 100.0,
                        backgroundColor: const Color(0xFF1E293B),
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          Color(0xFF38BDF8),
                        ),
                        minHeight: 4,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'MỨC DÙNG BỘ NHỚ',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          '${buildMode?['memory_usage'] ?? 0}%',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value:
                            ((buildMode?['memory_usage'] ?? 0) as num) / 100.0,
                        backgroundColor: const Color(0xFF1E293B),
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          Color(0xFF818CF8),
                        ),
                        minHeight: 4,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'ĐẦU VÀO ÂM THANH',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          '${buildMode?['audio_input'] ?? "K/D"}',
                          style: const TextStyle(
                            color: Color(0xFF00F0FF),
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ] else ...[
                    const SizedBox(height: 10),
                    const Text(
                      'CPU/Memory/Audio chưa khả dụng trên cloud - cần Desktop Execution Node (sắp ra mắt).',
                      style: TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 14,
                        height: 1.4,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatRow(String label, String value) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 15,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }

  Color _getAgentColor(String name) {
    final lower = name.toLowerCase();
    if (lower.contains('strategy')) return const Color(0xFFA855F7);
    if (lower.contains('research')) return const Color(0xFF38BDF8);
    if (lower.contains('marketing')) return const Color(0xFFF59E0B);
    if (lower.contains('dev') || lower.contains('code')) {
      return const Color(0xFF10B981);
    }
    if (lower.contains('finance')) return const Color(0xFFEAB308);
    return const Color(0xFF00F0FF);
  }
}

class _ConstellationGraphPainter extends CustomPainter {
  final double phase;

  _ConstellationGraphPainter({required this.phase});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width * 0.42;

    final nodePaint = Paint()
      ..color = const Color(0xFF00F0FF)
      ..style = PaintingStyle.fill;

    final linePaint = Paint()
      ..color = const Color(0xFF00F0FF).withValues(alpha: 0.25)
      ..strokeWidth = 0.8;

    const int nodeCount = 7;
    final List<Offset> nodes = [];

    for (int i = 0; i < nodeCount; i++) {
      final angle = (i * 2 * math.pi / nodeCount) + (phase * 2 * math.pi * 0.2);
      final r = radius * (0.5 + 0.5 * math.sin(i * 3 + phase * math.pi));
      nodes.add(
        Offset(
          center.dx + math.cos(angle) * r,
          center.dy + math.sin(angle) * r,
        ),
      );
    }

    // Draw connecting constellation lines
    for (int i = 0; i < nodeCount; i++) {
      for (int j = i + 1; j < nodeCount; j++) {
        final dist = (nodes[i] - nodes[j]).distance;
        if (dist < radius * 1.3) {
          linePaint.color = const Color(
            0xFF00F0FF,
          ).withValues(alpha: (1.0 - (dist / (radius * 1.3))) * 0.35);
          canvas.drawLine(nodes[i], nodes[j], linePaint);
        }
      }
    }

    // Draw glowing nodes
    for (int i = 0; i < nodeCount; i++) {
      final p = nodes[i];
      final glowPaint = Paint()
        ..color = const Color(0xFF00F0FF).withValues(alpha: 0.3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);

      canvas.drawCircle(p, 3.5, glowPaint);
      canvas.drawCircle(p, 1.8, nodePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _ConstellationGraphPainter oldDelegate) {
    return oldDelegate.phase != phase;
  }
}
