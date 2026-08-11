import 'package:flutter/material.dart';
import 'audio_waveform_painter.dart';
import 'hud_card.dart';
import 'artifact_card.dart';

class SystemHealthPanel extends StatefulWidget {
  final Map<String, dynamic>? data;
  final VoidCallback? onViewSubsystems;
  final VoidCallback? onViewActivity;

  const SystemHealthPanel({
    super.key,
    this.data,
    this.onViewSubsystems,
    this.onViewActivity,
  });

  @override
  State<SystemHealthPanel> createState() => _SystemHealthPanelState();
}

class _SystemHealthPanelState extends State<SystemHealthPanel> with SingleTickerProviderStateMixin {
  late AnimationController _waveController;

  @override
  void initState() {
    super.initState();
    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();
  }

  @override
  void dispose() {
    _waveController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final healthData = widget.data?['system_health'] as Map<String, dynamic>?;
    final voiceEngineData = widget.data?['voice_engine'] as Map<String, dynamic>?;
    final isVoiceReady = voiceEngineData?['status'] == 'READY';
    final subsystemsData = widget.data?['subsystems'] as Map<String, dynamic>?;
    final subsystemsList = (subsystemsData?['items'] as List<dynamic>?) ?? [];
    final recentActivity = (widget.data?['recent_activity'] as List<dynamic>?) ?? [];
    final recentArtifacts = (widget.data?['recent_artifacts'] as List<dynamic>?) ?? [];

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 1. SYSTEM HEALTH CARD
        hudCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              hudCardHeader(
                title: 'SYSTEM HEALTH',
                badgeText: healthData?['status'] ?? 'OPTIMAL',
                badgeColor: const Color(0xFF10B981),
              ),
              const SizedBox(height: 12),
              // Sync integrity isn't a real, measured signal yet (that's a
              // device-sync concept, blueprint V7+) - only latency/uptime,
              // which are genuinely measured server-side, are shown here.
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('LATENCY', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.w600)),
                  Text(
                    healthData?['latency_ms'] != null ? '${healthData!['latency_ms']}ms' : '—',
                    style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('UPTIME', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.w600)),
                  Text(
                    (healthData?['uptime'] as String?) ?? '—',
                    style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ],
          ),
        ),

        // 2. VOICE ENGINE CARD
        hudCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              hudCardHeader(
                title: 'VOICE ENGINE',
                badgeText: (voiceEngineData?['status'] as String?) ?? 'TEXT_ONLY',
                badgeColor: isVoiceReady ? const Color(0xFF00F0FF) : const Color(0xFF64748B),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: (isVoiceReady ? const Color(0xFF00F0FF) : const Color(0xFF64748B)).withValues(alpha: 0.12),
                      border: Border.all(
                        color: (isVoiceReady ? const Color(0xFF00F0FF) : const Color(0xFF64748B)).withValues(alpha: 0.5),
                        width: 1.5,
                      ),
                    ),
                    child: Icon(
                      isVoiceReady ? Icons.mic_none : Icons.mic_off_outlined,
                      color: isVoiceReady ? const Color(0xFF00F0FF) : const Color(0xFF64748B),
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          (voiceEngineData?['label'] as String?) ?? 'Voice input đang phát triển',
                          style: TextStyle(
                            color: isVoiceReady ? const Color(0xFF38BDF8) : const Color(0xFF94A3B8),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        // Only show a "live" waveform when voice is actually
                        // ready to capture audio - otherwise it falsely
                        // implies the mic is listening right now.
                        if (isVoiceReady) ...[
                          const SizedBox(height: 4),
                          AnimatedBuilder(
                            animation: _waveController,
                            builder: (context, child) {
                              return SizedBox(
                                height: 18,
                                child: CustomPaint(
                                  painter: AudioWaveformPainter(
                                    animationValue: _waveController.value,
                                    barCount: 16,
                                    primaryColor: const Color(0xFF00F0FF),
                                    secondaryColor: const Color(0xFF3B82F6),
                                  ),
                                ),
                              );
                            },
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        // 3. SUBSYSTEMS CARD
        hudCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              hudCardHeader(
                title: 'SUBSYSTEMS',
                badgeText: '${subsystemsData?['active_count'] ?? 7} / ${subsystemsData?['total_count'] ?? 7}',
                badgeColor: const Color(0xFF38BDF8),
              ),
              const SizedBox(height: 10),
              ...subsystemsList.take(7).map((item) {
                final name = item['name'] as String? ?? 'Subsystem';
                final health = item['health_percent'] as int? ?? 100;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6.0),
                  child: Row(
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: health >= 100 ? const Color(0xFF00F0FF) : const Color(0xFF38BDF8),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF00F0FF).withValues(alpha: 0.6),
                              blurRadius: 4,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          name,
                          style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        '$health%',
                        style: TextStyle(
                          color: health >= 100 ? const Color(0xFF00F0FF) : const Color(0xFF94A3B8),
                          fontSize: 11.5,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                );
              }),
              if (widget.onViewSubsystems != null) ...[
                const SizedBox(height: 4),
                InkWell(
                  onTap: widget.onViewSubsystems,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Text(
                          'VIEW DETAILS',
                          style: TextStyle(
                            color: Color(0xFF38BDF8),
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.0,
                          ),
                        ),
                        SizedBox(width: 4),
                        Icon(Icons.arrow_forward_ios, size: 10, color: Color(0xFF38BDF8)),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),

        // 4. ACTIVITY FEED CARD
        hudCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              hudCardHeader(
                title: 'ACTIVITY FEED',
                badgeText: '● LIVE',
                badgeColor: const Color(0xFFEF4444),
              ),
              const SizedBox(height: 10),
              ...recentActivity.take(4).map((act) {
                final time = act['timestamp'] as String? ?? '07:50';
                final actor = act['actor'] as String? ?? 'Agent';
                final action = act['action'] as String? ?? 'Activity';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        width: 6,
                        height: 6,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: Color(0xFFF59E0B),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        time,
                        style: const TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              actor,
                              style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 11.5, fontWeight: FontWeight.bold),
                            ),
                            Text(
                              action,
                              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }),
              if (widget.onViewActivity != null) ...[
                const SizedBox(height: 4),
                InkWell(
                  onTap: widget.onViewActivity,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Text(
                          'VIEW ALL',
                          style: TextStyle(
                            color: Color(0xFF38BDF8),
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.0,
                          ),
                        ),
                        SizedBox(width: 4),
                        Icon(Icons.arrow_forward_ios, size: 10, color: Color(0xFF38BDF8)),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),

        // 5. RECENT ARTIFACTS CARD (Outcome/Run/Artifact domain, §127-129)
        if (recentArtifacts.isNotEmpty)
          hudCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                hudCardHeader(
                  title: 'RECENT ARTIFACTS',
                  badgeText: '${recentArtifacts.length}',
                  badgeColor: const Color(0xFF00FFB2),
                ),
                const SizedBox(height: 10),
                ...recentArtifacts.take(3).map((art) {
                  final map = art as Map<String, dynamic>;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8.0),
                    child: ArtifactCard(
                      title: map['title'] as String? ?? 'Artifact',
                      type: map['type'] as String? ?? 'document',
                      status: map['status'] as String? ?? 'draft',
                      onTap: widget.onViewActivity,
                    ),
                  );
                }),
              ],
            ),
          ),
      ],
    );
  }
}
