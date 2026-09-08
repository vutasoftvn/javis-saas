import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/locale_controller.dart';
import '../../../../core/localization/supported_locale.dart';
import '../../../../core/theme/app_theme.dart';

/// Language switcher widget placed below auth form cards.
/// Displays a sleek glassmorphic card with a country flag and language text.
/// Clicking anywhere on the card automatically toggles between Vietnamese and English.
class AuthLanguageSwitcher extends StatefulWidget {
  const AuthLanguageSwitcher({super.key});

  @override
  State<AuthLanguageSwitcher> createState() => _AuthLanguageSwitcherState();
}

class _AuthLanguageSwitcherState extends State<AuthLanguageSwitcher> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final lc = Get.isRegistered<LocaleController>()
        ? Get.find<LocaleController>()
        : null;

    if (lc == null) {
      return const SizedBox.shrink();
    }

    return Obx(() {
      final currentLocale = lc.current.value;
      final isVi = currentLocale == SupportedLocale.viVN;
      final tooltipMessage = isVi ? 'Chuyển sang English' : 'Switch to Tiếng Việt';

      return Tooltip(
        message: tooltipMessage,
        child: MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) => setState(() => _isHovered = true),
          onExit: (_) => setState(() => _isHovered = false),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeInOut,
            decoration: BoxDecoration(
              color: _isHovered
                  ? AppTheme.surfaceDark.withValues(alpha: 0.92)
                  : AppTheme.surfaceDark.withValues(alpha: 0.75),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: _isHovered
                    ? AppTheme.primary.withValues(alpha: 0.65)
                    : AppTheme.primary.withValues(alpha: 0.28),
                width: 1.2,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primary.withValues(alpha: _isHovered ? 0.22 : 0.08),
                  blurRadius: _isHovered ? 20 : 14,
                  offset: const Offset(0, 4),
                ),
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.35),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Material(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(20),
              child: InkWell(
                key: const Key('auth_language_switcher'),
                borderRadius: BorderRadius.circular(20),
                onTap: () => lc.toggleLocale(),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    transitionBuilder: (child, animation) {
                      return FadeTransition(
                        opacity: animation,
                        child: ScaleTransition(
                          scale: Tween<double>(begin: 0.94, end: 1.0).animate(animation),
                          child: child,
                        ),
                      );
                    },
                    child: Row(
                      key: ValueKey<SupportedLocale>(currentLocale),
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Flag Icon Badge
                        _FlagBadge(isVi: isVi),
                        const SizedBox(width: 8),

                        // Language Text
                        Text(
                          isVi ? 'Tiếng Việt' : 'English',
                          key: const Key('auth_language_text'),
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: _isHovered ? Colors.white : Colors.white.withValues(alpha: 0.9),
                            letterSpacing: 0.3,
                          ),
                        ),
                        const SizedBox(width: 8),

                        // Subtle swap / toggle indicator icon
                        Icon(
                          Icons.swap_horiz_rounded,
                          key: const Key('auth_language_toggle_icon'),
                          size: 16,
                          color: _isHovered
                              ? AppTheme.primary
                              : AppTheme.primary.withValues(alpha: 0.75),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    });
  }
}

class _FlagBadge extends StatelessWidget {
  final bool isVi;

  const _FlagBadge({required this.isVi});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: isVi ? 'Cờ Việt Nam' : 'Cờ Hoa Kỳ',
      child: Container(
        key: const Key('auth_language_flag'),
        width: 22,
        height: 15,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(3),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.25),
            width: 0.6,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.3),
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(2.4),
          child: CustomPaint(
            painter: isVi ? const _VietnamFlagPainter() : const _UsFlagPainter(),
          ),
        ),
      ),
    );
  }
}

class _VietnamFlagPainter extends CustomPainter {
  const _VietnamFlagPainter();

  @override
  void paint(Canvas canvas, Size size) {
    // Red background
    final rect = Offset.zero & size;
    final bgPaint = Paint()..color = const Color(0xFFDA251D);
    canvas.drawRect(rect, bgPaint);

    // Centered golden yellow 5-point star
    final center = Offset(size.width / 2, size.height / 2);
    final outerRadius = size.height * 0.34;
    final innerRadius = outerRadius * 0.382;

    final path = Path();
    for (int i = 0; i < 10; i++) {
      final radius = i.isEven ? outerRadius : innerRadius;
      final angle = -math.pi / 2 + (i * math.pi / 5);
      final x = center.dx + radius * math.cos(angle);
      final y = center.dy + radius * math.sin(angle);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    path.close();

    final starPaint = Paint()
      ..color = const Color(0xFFFFCD00)
      ..style = PaintingStyle.fill;
    canvas.drawPath(path, starPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _UsFlagPainter extends CustomPainter {
  const _UsFlagPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    // Red background
    final redPaint = Paint()..color = const Color(0xFFB22234);
    canvas.drawRect(rect, redPaint);

    // 6 white stripes
    final whitePaint = Paint()..color = Colors.white;
    final stripeH = size.height / 13;
    for (int i = 1; i < 13; i += 2) {
      canvas.drawRect(
        Rect.fromLTWH(0, i * stripeH, size.width, stripeH),
        whitePaint,
      );
    }

    // Blue canton
    final cantonW = size.width * 0.44;
    final cantonH = stripeH * 7;
    final bluePaint = Paint()..color = const Color(0xFF3C3B6E);
    canvas.drawRect(
      Rect.fromLTWH(0, 0, cantonW, cantonH),
      bluePaint,
    );

    // White star dots in canton (3x3 grid)
    final dotPaint = Paint()..color = Colors.white;
    for (int r = 1; r <= 3; r++) {
      for (int c = 1; c <= 3; c++) {
        canvas.drawCircle(
          Offset(cantonW * c / 4, cantonH * r / 4),
          size.height * 0.045,
          dotPaint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

