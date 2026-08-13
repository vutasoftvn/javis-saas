import 'package:flutter/material.dart';
import 'package:frontend/core/theme/app_theme.dart';

enum AppButtonSize {
  small(36.0, 14.0, 12.0, 16.0),
  medium(44.0, 18.0, 14.0, 20.0),
  large(52.0, 24.0, 15.0, 24.0);

  final double height;
  final double horizontalPadding;
  final double fontSize;
  final double iconSize;

  const AppButtonSize(
    this.height,
    this.horizontalPadding,
    this.fontSize,
    this.iconSize,
  );
}

enum AppButtonVariant {
  primary,
  secondary,
  outlined,
  text,
  danger,
}

/// Standardized COSA OS Button Component
/// Enforces standard height specs (Small 36px, Medium 44px, Large 52px)
/// and bo góc 100 (BorderRadius.circular(100)).
class AppButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final AppButtonSize size;
  final IconData? icon;
  final bool isLoading;
  final bool isFullWidth;
  final bool showGlow;
  final Color? customBackgroundColor;
  final Color? customForegroundColor;

  const AppButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.size = AppButtonSize.medium,
    this.icon,
    this.isLoading = false,
    this.isFullWidth = false,
    this.showGlow = false,
    this.customBackgroundColor,
    this.customForegroundColor,
  });

  @override
  Widget build(BuildContext context) {
    final isDisabled = onPressed == null || isLoading;
    final borderRadius = BorderRadius.circular(100);

    Widget childContent = Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (isLoading) ...[
          SizedBox(
            width: size.iconSize,
            height: size.iconSize,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(
                _getForegroundColor(context, isDisabled),
              ),
            ),
          ),
          const SizedBox(width: 8),
        ] else if (icon != null) ...[
          Icon(
            icon,
            size: size.iconSize,
            color: _getForegroundColor(context, isDisabled),
          ),
          const SizedBox(width: 8),
        ],
        Text(
          label,
          style: TextStyle(
            fontSize: size.fontSize,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.3,
            color: _getForegroundColor(context, isDisabled),
          ),
        ),
      ],
    );

    ButtonStyle style = _getButtonStyle(context, borderRadius, isDisabled);

    Widget button;
    switch (variant) {
      case AppButtonVariant.primary:
      case AppButtonVariant.secondary:
      case AppButtonVariant.danger:
        button = ElevatedButton(
          onPressed: isDisabled ? null : onPressed,
          style: style,
          child: childContent,
        );
        break;
      case AppButtonVariant.outlined:
        button = OutlinedButton(
          onPressed: isDisabled ? null : onPressed,
          style: style,
          child: childContent,
        );
        break;
      case AppButtonVariant.text:
        button = TextButton(
          onPressed: isDisabled ? null : onPressed,
          style: style,
          child: childContent,
        );
        break;
    }

    if (showGlow && !isDisabled && variant == AppButtonVariant.primary) {
      return Container(
        decoration: BoxDecoration(
          borderRadius: borderRadius,
          boxShadow: [
            BoxShadow(
              color: AppTheme.primary.withValues(alpha: 0.4),
              blurRadius: 16,
              spreadRadius: 1,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: button,
      );
    }

    if (isFullWidth) {
      return SizedBox(
        width: double.infinity,
        child: button,
      );
    }

    return button;
  }

  Color _getForegroundColor(BuildContext context, bool isDisabled) {
    if (customForegroundColor != null) return customForegroundColor!;
    if (isDisabled) return AppTheme.textDimDark;

    switch (variant) {
      case AppButtonVariant.primary:
        return const Color(0xFF04070E);
      case AppButtonVariant.secondary:
        return AppTheme.textDark;
      case AppButtonVariant.outlined:
      case AppButtonVariant.text:
        return AppTheme.primary;
      case AppButtonVariant.danger:
        return Colors.white;
    }
  }

  ButtonStyle _getButtonStyle(
    BuildContext context,
    BorderRadius borderRadius,
    bool isDisabled,
  ) {
    final height = size.height;
    final padding = EdgeInsets.symmetric(horizontal: size.horizontalPadding);

    switch (variant) {
      case AppButtonVariant.primary:
        return ElevatedButton.styleFrom(
          backgroundColor: customBackgroundColor ?? AppTheme.primary,
          foregroundColor: _getForegroundColor(context, isDisabled),
          minimumSize: Size(isFullWidth ? double.infinity : 64, height),
          maximumSize: Size(double.infinity, height),
          padding: padding,
          elevation: showGlow ? 0 : 2,
          shape: RoundedRectangleBorder(borderRadius: borderRadius),
        );
      case AppButtonVariant.secondary:
        return ElevatedButton.styleFrom(
          backgroundColor: customBackgroundColor ?? AppTheme.surfaceDarkLighter,
          foregroundColor: _getForegroundColor(context, isDisabled),
          minimumSize: Size(isFullWidth ? double.infinity : 64, height),
          maximumSize: Size(double.infinity, height),
          padding: padding,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: borderRadius,
            side: const BorderSide(color: AppTheme.borderDark),
          ),
        );
      case AppButtonVariant.danger:
        return ElevatedButton.styleFrom(
          backgroundColor: customBackgroundColor ?? AppTheme.accent,
          foregroundColor: _getForegroundColor(context, isDisabled),
          minimumSize: Size(isFullWidth ? double.infinity : 64, height),
          maximumSize: Size(double.infinity, height),
          padding: padding,
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: borderRadius),
        );
      case AppButtonVariant.outlined:
        return OutlinedButton.styleFrom(
          foregroundColor: _getForegroundColor(context, isDisabled),
          minimumSize: Size(isFullWidth ? double.infinity : 64, height),
          maximumSize: Size(double.infinity, height),
          padding: padding,
          side: BorderSide(
            color: customBackgroundColor ?? AppTheme.borderGlow.withValues(alpha: 0.4),
          ),
          shape: RoundedRectangleBorder(borderRadius: borderRadius),
        );
      case AppButtonVariant.text:
        return TextButton.styleFrom(
          foregroundColor: _getForegroundColor(context, isDisabled),
          minimumSize: Size(isFullWidth ? double.infinity : 64, height),
          maximumSize: Size(double.infinity, height),
          padding: padding,
          shape: RoundedRectangleBorder(borderRadius: borderRadius),
        );
    }
  }
}
