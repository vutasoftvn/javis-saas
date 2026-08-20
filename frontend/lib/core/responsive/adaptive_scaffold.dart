import 'package:flutter/material.dart';
import 'breakpoints.dart';
import 'responsive_builder.dart';

/// COSA AdaptiveScaffold (Structure.md Mục 34 & 35)
/// Tự động thích ứng 1-pane (Mobile), 2-pane (Tablet), 3-pane (Desktop).
class AdaptiveScaffold extends StatefulWidget {
  final Widget leftPane;
  final Widget centerPane;
  final Widget rightPane;
  final String title;
  final double leftPaneWidth;
  final double rightPaneWidth;

  const AdaptiveScaffold({
    super.key,
    required this.leftPane,
    required this.centerPane,
    required this.rightPane,
    this.title = "COSA Hologram Hub",
    this.leftPaneWidth = 280.0,
    this.rightPaneWidth = 360.0,
  });

  @override
  State<AdaptiveScaffold> createState() => _AdaptiveScaffoldState();
}

class _AdaptiveScaffoldState extends State<AdaptiveScaffold> {
  int _mobileIndex = 1; // 0: Workforce, 1: Workspace, 2: Inspector

  @override
  Widget build(BuildContext context) {
    return ResponsiveLayoutBuilder(
      mobile: _buildMobileLayout,
      tablet: _buildTabletLayout,
      desktop: _buildDesktopLayout,
    );
  }

  Widget _buildDesktopLayout(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0D14),
      body: Row(
        children: [
          // Pane 1: Left Workforce & Sessions
          SizedBox(
            width: widget.leftPaneWidth,
            child: widget.leftPane,
          ),
          const VerticalDivider(width: 1, color: Color(0x1FFFFFFF)),
          // Pane 2: Center Interactive Workspace
          Expanded(
            child: widget.centerPane,
          ),
          const VerticalDivider(width: 1, color: Color(0x1FFFFFFF)),
          // Pane 3: Right Inspector & Trajectory
          SizedBox(
            width: widget.rightPaneWidth,
            child: widget.rightPane,
          ),
        ],
      ),
    );
  }

  Widget _buildTabletLayout(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0D14),
      appBar: AppBar(
        backgroundColor: const Color(0xFF101622),
        title: Text(widget.title, style: const TextStyle(color: Colors.white, fontSize: 16)),
        actions: [
          Builder(
            builder: (ctx) => IconButton(
              icon: const Icon(Icons.analytics_outlined, color: Color(0xFF00F0FF)),
              tooltip: "Mở Inspector Panel",
              onPressed: () => Scaffold.of(ctx).openEndDrawer(),
            ),
          ),
        ],
      ),
      drawer: Drawer(
        backgroundColor: const Color(0xFF0A0D14),
        child: widget.leftPane,
      ),
      endDrawer: Drawer(
        backgroundColor: const Color(0xFF0A0D14),
        child: widget.rightPane,
      ),
      body: widget.centerPane,
    );
  }

  Widget _buildMobileLayout(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0D14),
      body: IndexedStack(
        index: _mobileIndex,
        children: [
          widget.leftPane,
          widget.centerPane,
          widget.rightPane,
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        backgroundColor: const Color(0xFF101622),
        selectedItemColor: const Color(0xFF00F0FF),
        unselectedItemColor: Colors.white54,
        currentIndex: _mobileIndex,
        onTap: (index) => setState(() => _mobileIndex = index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.people_outline),
            label: "Workforce",
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.chat_bubble_outline),
            label: "Workspace",
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.timeline_outlined),
            label: "Inspector",
          ),
        ],
      ),
    );
  }
}
