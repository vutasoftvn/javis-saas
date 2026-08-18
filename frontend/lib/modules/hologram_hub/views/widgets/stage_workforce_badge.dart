import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// StageWorkforceBadge — Phase 6
/// Badge nhỏ hiển thị trên header Hub (cạnh Workforce pill).
/// Hiển thị số lượng exception OPEN + nháy đỏ khi có FOUNDER_GATE.
/// Click → mở ExceptionEscalationInbox.
class StageWorkforceBadge extends StatefulWidget {
  final RxBool hasActiveEscalations;
  final RxBool hasCriticalEscalation;
  final RxList<Map<String, dynamic>> openEscalations;
  final VoidCallback onTap;
  final String? currentStageCode;
  final VoidCallback? onStageRosterTap;

  const StageWorkforceBadge({
    super.key,
    required this.hasActiveEscalations,
    required this.hasCriticalEscalation,
    required this.openEscalations,
    required this.onTap,
    this.currentStageCode,
    this.onStageRosterTap,
  });

  @override
  State<StageWorkforceBadge> createState() => _StageWorkforceBadgeState();
}

class _StageWorkforceBadgeState extends State<StageWorkforceBadge>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnim;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);

    _pulseAnim = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Stage Roster pill (nếu có stage code)
        if (widget.currentStageCode != null && widget.onStageRosterTap != null)
          GestureDetector(
            onTap: widget.onStageRosterTap,
            child: Container(
              margin: const EdgeInsets.only(right: 6),
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF1E1B4B), Color(0xFF2D1B69)],
                ),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: const Color(0xFF6C63FF).withValues(alpha: 0.4),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.layers_outlined,
                    size: 12,
                    color: Color(0xFF9C8FFF),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    widget.currentStageCode!,
                    style: TextStyle(
                      color: const Color(0xFF9C8FFF),
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ),

        // Exception escalation badge
        Obx(() {
          final hasActive = widget.hasActiveEscalations.value;
          final hasCritical = widget.hasCriticalEscalation.value;
          final count = widget.openEscalations.length;

          if (!hasActive) {
            // Healthy state — xanh lục nhỏ
            return GestureDetector(
              onTap: widget.onTap,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFF22C55E).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFF22C55E).withValues(alpha: 0.3),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Color(0xFF22C55E),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      'Bình thường',
                      style: TextStyle(
                        color: const Color(0xFF22C55E),
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }

          // Has exceptions — hiện badge với count
          return GestureDetector(
            onTap: widget.onTap,
            child: AnimatedBuilder(
              animation: _pulseAnim,
              builder: (_, _) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                  decoration: BoxDecoration(
                    color: hasCritical
                        ? Color.lerp(
                            const Color(0xFFEF4444).withValues(alpha: 0.1),
                            const Color(0xFFEF4444).withValues(alpha: 0.25),
                            _pulseAnim.value,
                          )!
                        : const Color(0xFFEAB308).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: hasCritical
                          ? Color.lerp(
                              const Color(0xFFEF4444).withValues(alpha: 0.3),
                              const Color(0xFFEF4444).withValues(alpha: 0.7),
                              _pulseAnim.value,
                            )!
                          : const Color(0xFFEAB308).withValues(alpha: 0.4),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Blinking dot
                      AnimatedBuilder(
                        animation: _pulseAnim,
                        builder: (_, _) => Container(
                          width: 7,
                          height: 7,
                          decoration: BoxDecoration(
                            color: hasCritical
                                ? Color.lerp(
                                    const Color(0xFFEF4444).withValues(alpha: 0.5),
                                    const Color(0xFFEF4444),
                                    _pulseAnim.value,
                                  )
                                : const Color(0xFFEAB308),
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                      const SizedBox(width: 5),
                      Text(
                        hasCritical
                            ? '🚨 $count Exception'
                            : '⚠ $count Exception',
                        style: TextStyle(
                          color: hasCritical
                              ? const Color(0xFFEF4444)
                              : const Color(0xFFEAB308),
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          );
        }),
      ],
    );
  }
}
