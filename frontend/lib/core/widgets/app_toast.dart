import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../theme/app_theme.dart';

enum ToastType {
  success,
  error,
  warning,
  info,
}

/// Shared Toast Notification Component (COSA Design System)
/// Displays a sleek glassmorphic toast notification at the Top-Right corner.
class AppToast {
  static void success(
    String message, {
    String? title = 'Thành công',
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title,
      type: ToastType.success,
      duration: duration,
      onTap: onTap,
    );
  }

  static void error(
    String message, {
    String? title = 'Đã có lỗi xảy ra',
    Duration? duration = const Duration(seconds: 5),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title,
      type: ToastType.error,
      duration: duration,
      onTap: onTap,
    );
  }

  static void warning(
    String message, {
    String? title = 'Cảnh báo',
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title,
      type: ToastType.warning,
      duration: duration,
      onTap: onTap,
    );
  }

  static void info(
    String message, {
    String? title = 'Thông báo',
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title,
      type: ToastType.info,
      duration: duration,
      onTap: onTap,
    );
  }

  static void show({
    required String message,
    String? title,
    ToastType type = ToastType.info,
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    // Safety check if Get overlay context is not available (e.g. unit tests without UI)
    if (Get.testMode || (Get.context == null && Get.overlayContext == null)) {
      debugPrint('[AppToast] [${type.name.toUpperCase()}] $title: $message');
      return;
    }

    try {
      final Color accentColor = _getAccentColor(type);
      final IconData icon = _getIcon(type);

      double screenWidth = 400;
      final ctx = Get.context ?? Get.overlayContext;
      if (ctx != null) {
        screenWidth = MediaQuery.of(ctx).size.width;
      }

      const double toastWidth = 400.0;
      final double leftMargin = screenWidth > (toastWidth + 40)
          ? screenWidth - toastWidth - 20
          : 16.0;

      Get.rawSnackbar(
        snackPosition: SnackPosition.TOP,
        backgroundColor: Colors.transparent,
        margin: EdgeInsets.only(
          top: 16,
          right: 16,
          left: leftMargin,
          bottom: 0,
        ),
        padding: EdgeInsets.zero,
        duration: duration ?? const Duration(seconds: 4),
        isDismissible: true,
        messageText: _ToastWidget(
          title: title,
          message: message,
          accentColor: accentColor,
          icon: icon,
          onTap: onTap,
          onClose: () {
            if (Get.isSnackbarOpen) {
              Get.closeCurrentSnackbar();
            }
          },
        ),
      );
    } catch (e) {
      debugPrint('[AppToast] Error displaying toast: $e');
    }
  }

  static Color _getAccentColor(ToastType type) {
    switch (type) {
      case ToastType.success:
        return AppTheme.success;
      case ToastType.error:
        return AppTheme.error;
      case ToastType.warning:
        return AppTheme.warning;
      case ToastType.info:
        return AppTheme.info;
    }
  }

  static IconData _getIcon(ToastType type) {
    switch (type) {
      case ToastType.success:
        return Icons.check_circle_rounded;
      case ToastType.error:
        return Icons.error_rounded;
      case ToastType.warning:
        return Icons.warning_amber_rounded;
      case ToastType.info:
        return Icons.info_rounded;
    }
  }
}

class _ToastWidget extends StatelessWidget {
  final String? title;
  final String message;
  final Color accentColor;
  final IconData icon;
  final VoidCallback? onTap;
  final VoidCallback onClose;

  const _ToastWidget({
    this.title,
    required this.message,
    required this.accentColor,
    required this.icon,
    this.onTap,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: accentColor.withValues(alpha: 0.35),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.45),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
              BoxShadow(
                color: accentColor.withValues(alpha: 0.12),
                blurRadius: 12,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left Accent Indicator Bar
                  Container(
                    width: 4,
                    color: accentColor,
                  ),
                  const SizedBox(width: 12),

                  // Status Icon
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: accentColor.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        icon,
                        size: 20,
                        color: accentColor,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Content (Title & Message)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (title != null && title!.isNotEmpty) ...[
                            Text(
                              title!,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textDark,
                                letterSpacing: 0.2,
                              ),
                            ),
                            const SizedBox(height: 3),
                          ],
                          Text(
                            message,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w400,
                              color: AppTheme.textMutedDark,
                              height: 1.35,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Dismiss Button
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: IconButton(
                      icon: const Icon(
                        Icons.close_rounded,
                        size: 16,
                        color: AppTheme.textDimDark,
                      ),
                      splashRadius: 16,
                      tooltip: 'Đóng',
                      onPressed: onClose,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
