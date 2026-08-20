/// COSA Responsive Breakpoints (Structure.md Mục 35)
class ResponsiveBreakpoints {
  static const double mobileMax = 768.0;
  static const double tabletMax = 1200.0;

  static bool isMobile(double width) => width < mobileMax;
  static bool isTablet(double width) => width >= mobileMax && width < tabletMax;
  static bool isDesktop(double width) => width >= tabletMax;
}
