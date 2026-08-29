import 'package:flutter/material.dart';
import '../miva_hologram_core.dart';

typedef HologramPalette = ({Color primary, Color secondary, Color accent});

HologramPalette resolveHologramPalette({
  required HologramRuntimeState runtimeState,
  required double hueProgress,
}) {
  final huePrimary = (hueProgress * 360.0) % 360.0;
  final hueSecondary = (huePrimary + 60.0) % 360.0;
  final hueAccent = (huePrimary + 180.0) % 360.0;

  final dynamicRainbowColor = HSVColor.fromAHSV(
    0.85,
    huePrimary,
    0.70,
    0.95,
  ).toColor();

  final secondaryDynamicColor = HSVColor.fromAHSV(
    0.80,
    hueSecondary,
    0.65,
    0.90,
  ).toColor();

  final accentDynamicColor = HSVColor.fromAHSV(
    0.90,
    hueAccent,
    0.85,
    1.00,
  ).toColor();

  switch (runtimeState) {
    case HologramRuntimeState.listening:
      return (
        primary: const Color(0xFF00FFB2),
        secondary: const Color(0xFF00E5FF),
        accent: const Color(0xFF10B981),
      );
    case HologramRuntimeState.speaking:
      return (
        primary: const Color(0xFF00E5FF),
        secondary: const Color(0xFF7C3AED),
        accent: const Color(0xFF38BDF8),
      );
    case HologramRuntimeState.thinking:
      return (
        primary: const Color(0xFF818CF8),
        secondary: const Color(0xFFC084FC),
        accent: const Color(0xFFA855F7),
      );
    case HologramRuntimeState.acting:
      return (
        primary: const Color(0xFFF59E0B),
        secondary: const Color(0xFFEC4899),
        accent: const Color(0xFFFB923C),
      );
    case HologramRuntimeState.retrieving:
      return (
        primary: const Color(0xFF06B6D4),
        secondary: const Color(0xFF3B82F6),
        accent: const Color(0xFF22D3EE),
      );
    case HologramRuntimeState.waitingApproval:
      return (
        primary: const Color(0xFFF59E0B),
        secondary: const Color(0xFFD97706),
        accent: const Color(0xFFFBBF24),
      );
    case HologramRuntimeState.success:
      return (
        primary: const Color(0xFF10B981),
        secondary: const Color(0xFF059669),
        accent: const Color(0xFF34D399),
      );
    case HologramRuntimeState.warning:
      return (
        primary: const Color(0xFFF59E0B),
        secondary: const Color(0xFFEA580C),
        accent: const Color(0xFFFCD34D),
      );
    case HologramRuntimeState.error:
      return (
        primary: const Color(0xFFEF4444),
        secondary: const Color(0xFFDC2626),
        accent: const Color(0xFFF87171),
      );
    case HologramRuntimeState.offline:
      return (
        primary: const Color(0xFF64748B),
        secondary: const Color(0xFF475569),
        accent: const Color(0xFF94A3B8),
      );
    case HologramRuntimeState.genesis:
      return (
        primary: const Color(0xFF0EA5E9).withValues(alpha: 0.8),
        secondary: const Color(0xFF06B6D4),
        accent: const Color(0xFF38BDF8),
      );
    case HologramRuntimeState.idle:
      return (
        primary: dynamicRainbowColor,
        secondary: secondaryDynamicColor,
        accent: accentDynamicColor,
      );
  }
}
