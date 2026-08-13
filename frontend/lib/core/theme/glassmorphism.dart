import 'dart:ui';
import 'package:flutter/material.dart';

class Glassmorphism extends StatelessWidget {
  final Widget child;
  final double blur;
  final double opacity;
  final BorderRadius? borderRadius;
  final Color color;
  final BoxBorder? border;

  const Glassmorphism({
    super.key,
    required this.child,
    this.blur = 10,
    this.opacity = 0.1,
    this.borderRadius,
    this.color = Colors.white,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius ?? BorderRadius.zero,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          decoration: BoxDecoration(
            color: color.withValues(alpha: opacity),
            borderRadius: borderRadius,
            border: border ??
                Border.all(
                  color: color.withValues(alpha: (opacity * 1.5).clamp(0.0, 1.0)),
                  width: 1.0,
                ),
          ),
          child: child,
        ),
      ),
    );
  }
}
