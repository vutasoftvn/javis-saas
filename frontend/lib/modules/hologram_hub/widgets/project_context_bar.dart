import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ProjectContextBar extends StatefulWidget {
  final List<dynamic> projects;
  final Rx<String?> selectedProjectId;
  final Function(String projectId) onSelected;

  const ProjectContextBar({
    Key? key,
    required this.projects,
    required this.selectedProjectId,
    required this.onSelected,
  }) : super(key: key);

  @override
  State<ProjectContextBar> createState() => _ProjectContextBarState();
}

class _ProjectContextBarState extends State<ProjectContextBar> {
  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final selectedId = widget.selectedProjectId.value;
      final selectedProject = selectedId != null
          ? widget.projects.firstWhereOrNull(
              (p) => p['id']?.toString() == selectedId,
            )
          : null;

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A).withValues(alpha: 0.95),
          border: Border(
            bottom: BorderSide(
              color: const Color(0xFF6366F1).withValues(alpha: 0.3),
              width: 1,
            ),
          ),
        ),
        child: Row(
          children: [
            // Workspace name
            Flexible(
              child: Text(
                'Workspace',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 13,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 12),
            const Text('·', style: TextStyle(color: Colors.white54)),
            const SizedBox(width: 12),

            // Project selector
            Expanded(
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  key: const Key('project_context_selector'),
                  onTap: () => _showProjectPicker(context),
                  child: _buildProjectSelector(selectedProject),
                ),
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildProjectSelector(dynamic selectedProject) {
    if (selectedProject == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(
          'Select Project',
          style: TextStyle(
            color: const Color(0xFF6366F1).withValues(alpha: 0.8),
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
      );
    }

    final title = selectedProject['title']?.toString() ?? 'Project';
    final stage = selectedProject['lifecycleStage'] ??
        selectedProject['project_stage'] ??
        selectedProject['lifecycle_stage'] ??
        'Unknown';

    return Row(
      children: [
        Expanded(
          child: Text(
            'Project: $title',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: const Color(0xFF6366F1).withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            stage.toString(),
            style: TextStyle(
              color: const Color(0xFF6366F1),
              fontSize: 11,
            ),
          ),
        ),
        const SizedBox(width: 8),
        const Icon(Icons.keyboard_arrow_down, size: 18, color: Colors.white70),
      ],
    );
  }

  void _showProjectPicker(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(16),
        decoration: const BoxDecoration(
          color: Color(0xFF0F172A),
          borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        ),
        child: ListView.builder(
          itemCount: widget.projects.length,
          itemBuilder: (_, i) {
            final project = widget.projects[i];
            final title = project['title']?.toString() ?? 'Project ${i + 1}';
            return ListTile(
              title: Text(
                title,
                style: const TextStyle(color: Colors.white),
              ),
              onTap: () {
                widget.onSelected(project['id']?.toString() ?? '');
                Navigator.pop(ctx);
              },
            );
          },
        ),
      ),
    );
  }
}
