import 'package:flutter/material.dart';
import '../../../../shared/widgets/trajectory/trajectory_timeline_view.dart';

class RightInspectorPane extends StatefulWidget {
  final List<Map<String, dynamic>> trajectorySteps;
  final Map<String, dynamic>? activeStep;
  final Function(Map<String, dynamic> step)? onStepSelected;

  const RightInspectorPane({
    super.key,
    required this.trajectorySteps,
    this.activeStep,
    this.onStepSelected,
  });

  @override
  State<RightInspectorPane> createState() => _RightInspectorPaneState();
}

class _RightInspectorPaneState extends State<RightInspectorPane> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0D121D),
      child: Column(
        children: [
          // Inspector Header Tabs
          Container(
            decoration: const BoxDecoration(
              color: Color(0xFF101622),
              border: Border(bottom: BorderSide(color: Color(0x1FFFFFFF))),
            ),
            child: TabBar(
              controller: _tabController,
              indicatorColor: const Color(0xFF00F0FF),
              labelColor: const Color(0xFF00F0FF),
              unselectedLabelColor: Colors.white54,
              labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              tabs: const [
                Tab(icon: Icon(Icons.timeline, size: 16), text: "TRAJECTORY"),
                Tab(icon: Icon(Icons.info_outline, size: 16), text: "INSPECTOR"),
              ],
            ),
          ),

          // Tab Views
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                // Tab 1: Live Trajectory Timeline
                TrajectoryTimelineView(
                  steps: widget.trajectorySteps,
                  onStepSelected: widget.onStepSelected,
                ),

                // Tab 2: Selected Step Inspector
                widget.activeStep != null
                    ? SingleChildScrollView(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.activeStep!['title'] ?? 'Chi tiết bước',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: const Color(0x15FFFFFF),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                widget.activeStep!['description'] ?? widget.activeStep.toString(),
                                style: const TextStyle(color: Colors.white70, fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      )
                    : const Center(
                        child: Text(
                          "Chọn một bước trên Timeline để xem chi tiết.",
                          style: TextStyle(color: Colors.white38, fontSize: 12),
                        ),
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
