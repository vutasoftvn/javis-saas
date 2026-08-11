import 'package:flutter/material.dart';

/// Standard Javis OS Theme System (Stark Cyberpunk Dark)
/// Cohesive visual language based on the COSA Hologram Hub design tokens.
class AppTheme {
  // Brand Neon & Accent Colors
  static const Color primary = Color(0xFF00F0FF); // Electric Neon Cyan
  static const Color primaryLight = Color(0xFF38BDF8); // Sky 400
  static const Color primaryDark = Color(0xFF0072FF); // Deep Cyan/Blue
  static const Color secondary = Color(0xFF38BDF8); // Sky Blue
  static const Color secondaryLight = Color(0xFF7DD3FC); // Sky 300
  static const Color secondaryDark = Color(0xFF0284C7); // Sky 600
  static const Color accent = Color(0xFFF43F5E); // Rose 500
  static const Color accentLight = Color(0xFFFB7185); // Rose 400

  // Semantic Status Colors
  static const Color success = Color(0xFF10B981); // Emerald 500
  static const Color warning = Color(0xFFF59E0B); // Amber 500
  static const Color error = Color(0xFFF43F5E); // Rose 500
  static const Color info = Color(0xFF38BDF8); // Sky 400
  static const Color preview = Color(0xFF64748B); // Slate 500

  // Dark Canvas & Surfaces (Matching Hologram Hub Deep Space theme)
  static const Color backgroundDark = Color(0xFF070C18); // Root Deep Canvas
  static const Color backgroundDarker = Color(0xFF04070E); // Deepest Black-Blue
  static const Color surfaceDark = Color(0xFF0D172A); // Main Card & Sidebar Surface
  static const Color surfaceDarkHeader = Color(0xFF080F1E); // Header Bar & Command Bar Surface
  static const Color surfaceDarkLighter = Color(0xFF141C2E); // Nested Card Container Surface
  static const Color surfaceDarkElevated = Color(0xFF1E293B); // Tooltips & Popups
  static const Color borderDark = Color(0xFF1E293B); // Standard Subtle Border (1px)
  static const Color borderGlow = Color(0xFF00F0FF); // Highlight & Glow Border

  // Typography & Text Colors
  static const Color textDark = Color(0xFFFFFFFF); // Primary Pure White
  static const Color textMutedDark = Color(0xFF94A3B8); // Slate 400 Muted Text
  static const Color textDimDark = Color(0xFF64748B); // Slate 500 Dim Text
  static const Color textAccent = Color(0xFF00F0FF); // Neon Cyan Accent Text

  // Standard Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF00D2FF), Color(0xFF0072FF)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cyanGradient = LinearGradient(
    colors: [Color(0xFF00F0FF), Color(0xFF38BDF8)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const RadialGradient backgroundRadialGradient = RadialGradient(
    center: Alignment(0.0, -0.2),
    radius: 1.2,
    colors: [
      Color(0xFF0B1934),
      Color(0xFF070C18),
      Color(0xFF04070E),
    ],
    stops: [0.0, 0.65, 1.0],
  );

  static const LinearGradient backgroundLinearGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0B1934),
      Color(0xFF070C18),
      Color(0xFF04070E),
    ],
  );

  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0D172A),
      Color(0xFF080F1E),
    ],
  );

  static LinearGradient get glowGradient => LinearGradient(
    colors: [
      primary.withValues(alpha: 0.15),
      Colors.transparent,
    ],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // Standard Box Decorations
  static BoxDecoration get hudCardDecoration => BoxDecoration(
    color: surfaceDark.withValues(alpha: 0.85),
    borderRadius: BorderRadius.circular(14),
    border: Border.all(color: borderDark, width: 1.0),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withValues(alpha: 0.25),
        blurRadius: 10,
        offset: const Offset(0, 2),
      ),
    ],
  );

  static BoxDecoration get hudHeaderDecoration => const BoxDecoration(
    color: surfaceDarkHeader,
    border: Border(bottom: BorderSide(color: borderDark)),
  );

  static BoxDecoration get glowButtonDecoration => BoxDecoration(
    gradient: primaryGradient,
    borderRadius: BorderRadius.circular(12),
    boxShadow: [
      BoxShadow(
        color: primary.withValues(alpha: 0.35),
        blurRadius: 16,
        spreadRadius: 1,
        offset: const Offset(0, 2),
      ),
    ],
  );

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: backgroundDark,
      canvasColor: backgroundDark,
      cardColor: surfaceDark,
      dividerColor: borderDark,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: secondary,
        surface: surfaceDark,
        error: accent,
        onPrimary: Color(0xFF04070E),
        onSecondary: Color(0xFF04070E),
        onSurface: textDark,
        outline: borderDark,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surfaceDarkHeader,
        elevation: 0,
        centerTitle: true,
        iconTheme: IconThemeData(color: textDark),
        titleTextStyle: TextStyle(
          color: textDark,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceDark,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: borderDark),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surfaceDark,
        elevation: 16,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: borderGlow.withValues(alpha: 0.35)),
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: surfaceDark,
        elevation: 12,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: borderDark),
        ),
        textStyle: const TextStyle(color: textDark, fontSize: 13),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: backgroundDark,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: borderDark),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: borderDark),
        ),
        focusedBorder: const OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(10)),
          borderSide: BorderSide(color: primary, width: 1.5),
        ),
        labelStyle: const TextStyle(color: textMutedDark, fontSize: 13),
        hintStyle: const TextStyle(color: textDimDark, fontSize: 13),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: const Color(0xFF04070E),
          elevation: 4,
          shadowColor: primary.withValues(alpha: 0.35),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: BorderSide(color: borderGlow.withValues(alpha: 0.35)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return primary;
          }
          return Colors.transparent;
        }),
        checkColor: WidgetStateProperty.all(const Color(0xFF04070E)),
        side: const BorderSide(color: textMutedDark),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
      ),
      dividerTheme: const DividerThemeData(
        color: borderDark,
        thickness: 1,
        space: 1,
      ),
      tabBarTheme: const TabBarThemeData(
        labelColor: primary,
        unselectedLabelColor: textMutedDark,
        indicatorColor: primary,
        indicatorSize: TabBarIndicatorSize.tab,
        dividerColor: borderDark,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: surfaceDarkElevated,
        contentTextStyle: const TextStyle(color: textDark, fontSize: 13),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: borderDark),
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}

