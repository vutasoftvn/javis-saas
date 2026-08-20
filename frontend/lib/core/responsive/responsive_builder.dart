import 'package:flutter/material.dart';
import 'breakpoints.dart';

typedef ResponsiveWidgetBuilder = Widget Function(BuildContext context);

class ResponsiveLayoutBuilder extends StatelessWidget {
  final ResponsiveWidgetBuilder mobile;
  final ResponsiveWidgetBuilder? tablet;
  final ResponsiveWidgetBuilder desktop;

  const ResponsiveLayoutBuilder({
    super.key,
    required this.mobile,
    this.tablet,
    required this.desktop,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        if (ResponsiveBreakpoints.isDesktop(width)) {
          return desktop(context);
        } else if (ResponsiveBreakpoints.isTablet(width)) {
          return (tablet ?? desktop)(context);
        } else {
          return mobile(context);
        }
      },
    );
  }
}
