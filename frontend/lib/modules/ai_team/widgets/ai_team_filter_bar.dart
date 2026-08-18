import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamFilterBar extends StatelessWidget {
  final AiTeamController controller;

  const AiTeamFilterBar({
    super.key,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    // Obx bắt buộc để widget rebuild khi selectedDepartment thay đổi
    return Obx(() {
      final totalCount = controller.agents.length;
      final coreCount =
          controller.agents.where((a) => a['is_system'] != false).length;
      final customCount =
          controller.agents.where((a) => a['is_system'] == false).length;

      final depts = [
        {'key': 'ALL', 'label': 'Tất cả ($totalCount)'},
        {'key': 'CORE', 'label': 'Core Team ($coreCount)'},
        if (customCount > 0)
          {'key': 'CUSTOM', 'label': 'Tùy biến ($customCount)'},
        {'key': 'EXECUTIVE', 'label': 'Điều hành'},
        {'key': 'FINANCE', 'label': 'Tài chính'},
        {'key': 'GROWTH', 'label': 'Marketing & Growth'},
        {'key': 'SALES', 'label': 'Sales & CRM'},
        {'key': 'TECH', 'label': 'Kỹ thuật & Code'},
        {'key': 'OPERATIONS', 'label': 'Pháp lý & Vận hành'},
      ];

      final selected = controller.selectedDepartment.value;

      return Center(
        child: Container(
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(100),
            border:
                Border.all(color: AppTheme.borderDark.withValues(alpha: 0.8)),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: depts.map((d) {
                final isSelected = selected == d['key'];
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(100),
                      onTap: () =>
                          controller.selectedDepartment.value = d['key']!,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        curve: Curves.easeInOut,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 6.5),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? AppTheme.primary.withValues(alpha: 0.2)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(100),
                          border: Border.all(
                            color: isSelected
                                ? AppTheme.primary
                                : Colors.transparent,
                            width: 1.2,
                          ),
                          boxShadow: isSelected
                              ? [
                                  BoxShadow(
                                    color:
                                        AppTheme.primary.withValues(alpha: 0.15),
                                    blurRadius: 8,
                                    offset: const Offset(0, 2),
                                  ),
                                ]
                              : null,
                        ),
                        child: Text(
                          d['label']!,
                          style: TextStyle(
                            color: isSelected
                                ? AppTheme.primary
                                : AppTheme.textMutedDark,
                            fontWeight: isSelected
                                ? FontWeight.bold
                                : FontWeight.w500,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ),
      );
    });
  }
}
