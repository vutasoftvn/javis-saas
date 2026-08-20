import 'package:flutter/material.dart';
import 'trajectory_step_tile.dart';

class TrajectoryTimelineView extends StatelessWidget {
  final List<Map<String, dynamic>> steps;
  final Function(Map<String, dynamic> step)? onStepSelected;

  const TrajectoryTimelineView({
    super.key,
    required this.steps,
    this.onStepSelected,
  });

  @override
  Widget build(BuildContext context) {
    if (steps.isEmpty) {
      return const Center(
        child: Text(
          "Chưa có bước thực thi nào.",
          style: TextStyle(color: Colors.white38, fontSize: 12),
        ),
      );
    }

    return ListView.builder(
      itemCount: steps.length,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      itemBuilder: (context, index) {
        final step = steps[index];
        return TrajectoryStepTile(
          step: step,
          onTap: () => onStepSelected?.call(step),
        );
      },
    );
  }
}
