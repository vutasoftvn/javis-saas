import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';
import 'ai_team_agent_card.dart';
import 'ai_team_agent_studio_dialog.dart';

class AiTeamAgentsGrid extends StatelessWidget {
  final AiTeamController controller;

  const AiTeamAgentsGrid({
    super.key,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    // Obx bắt buộc: filteredAgents phụ thuộc vào selectedDepartment (Rx)
    return Obx(() {
      final agentsList = controller.filteredAgents;

      if (agentsList.isEmpty) {
        return Container(
          padding: const EdgeInsets.all(32),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: const Text(
            'Không có Agent nào thuộc phòng ban này.',
            style: TextStyle(color: AppTheme.textMutedDark),
          ),
        );
      }

      return LayoutBuilder(
        builder: (context, constraints) {
          final crossAxisCount = constraints.maxWidth > 1200
              ? 3
              : (constraints.maxWidth > 750 ? 2 : 1);
          const spacing = 12.0;

          // Build full items list (agents + add card)
          final allItems = <Widget>[
            ...agentsList.map((agent) => AiTeamAgentCard(
                  agent: agent,
                  controller: controller,
                )),
            _AddAgentCard(
                onTap: () =>
                    AiTeamAgentStudioDialog.show(context, controller)),
          ];

          // Chunk into rows
          final rows = <List<Widget>>[];
          for (var i = 0; i < allItems.length; i += crossAxisCount) {
            rows.add(
              allItems.sublist(
                i,
                (i + crossAxisCount).clamp(0, allItems.length),
              ),
            );
          }

          return Column(
            children: rows.map((rowItems) {
              return Padding(
                padding: const EdgeInsets.only(bottom: spacing),
                child: IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (var j = 0; j < rowItems.length; j++) ...[
                        if (j > 0) const SizedBox(width: spacing),
                        Expanded(child: rowItems[j]),
                      ],
                      // Fill empty slots in last incomplete row
                      for (var k = rowItems.length; k < crossAxisCount; k++) ...[
                        const SizedBox(width: spacing),
                        const Expanded(child: SizedBox.shrink()),
                      ],
                    ],
                  ),
                ),
              );
            }).toList(),
          );
        },
      );
    });
  }
}

class _AddAgentCard extends StatelessWidget {
  final VoidCallback onTap;
  const _AddAgentCard({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
          constraints: const BoxConstraints(minHeight: 120),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: AppTheme.primary.withValues(alpha: 0.3),
              style: BorderStyle.solid,
              width: 1.5,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                  border: Border.all(
                      color: AppTheme.primary.withValues(alpha: 0.4)),
                ),
                child: const Center(
                  child: Icon(Icons.person_add_alt_1_rounded,
                      color: AppTheme.primary, size: 24),
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                '+ Bổ sung Nhân sự AI',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Tạo Agent chuyên môn theo ngành hàng hoặc vị trí riêng của bạn',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
