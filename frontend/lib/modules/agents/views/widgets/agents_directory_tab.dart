import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/ui/layout_breakpoints.dart';
import '../../controllers/agents_controller.dart';
import 'agent_card.dart';

class AgentsDirectoryTab extends StatelessWidget {
  final AgentsController controller;
  final List<String> departments;

  const AgentsDirectoryTab({
    super.key,
    required this.controller,
    required this.departments,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Filter Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
          ),
          child: Row(
            children: [
              const Text('Phòng ban:', style: TextStyle(color: Colors.grey, fontSize: 13, fontWeight: FontWeight.w600)),
              const SizedBox(width: 12),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: departments.map((dept) {
                      return Obx(() {
                        final isSelected = controller.selectedDepartment.value == dept;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: FilterChip(
                            label: Text(dept),
                            selected: isSelected,
                            onSelected: (_) => controller.filterByDepartment(dept),
                            selectedColor: Colors.blueAccent,
                            backgroundColor: const Color(0xFF1E293B),
                            labelStyle: TextStyle(
                              fontSize: 12.5,
                              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                              color: isSelected ? Colors.white : Colors.grey.shade400,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(20),
                              side: BorderSide(
                                color: isSelected ? Colors.blueAccent : const Color(0xFF334155),
                              ),
                            ),
                          ),
                        );
                      });
                    }).toList(),
                  ),
                ),
              ),
            ],
          ),
        ),

        // Grid View
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator(color: Colors.blueAccent));
            }
            if (controller.filteredAgents.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.person_search_outlined, size: 48, color: Colors.grey.shade600),
                    const SizedBox(height: 12),
                    Text('Không tìm thấy Agent nào trong phòng ban này.', style: TextStyle(color: Colors.grey.shade400)),
                  ],
                ),
              );
            }

            return LayoutBuilder(
              builder: (ctx, constraints) {
                // Task 10 — thay ngưỡng width tự chọn (900/600/1400) bằng
                // `layoutForWidth` dùng chung toàn app. Bậc `expanded` giữ
                // thêm một mốc phụ 1400 để tận dụng màn hình rất rộng (4
                // cột) — không phải một bậc mới trong `AppLayout`, chỉ là
                // tinh chỉnh trong nội bộ bậc expanded.
                final layout = layoutForWidth(constraints.maxWidth);
                int crossAxisCount = switch (layout) {
                  AppLayout.compact => 1,
                  AppLayout.medium => 2,
                  AppLayout.expanded => constraints.maxWidth > 1400 ? 4 : 3,
                };

                return GridView.builder(
                  padding: const EdgeInsets.all(24),
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: crossAxisCount,
                    crossAxisSpacing: 18,
                    mainAxisSpacing: 18,
                    mainAxisExtent: 220,
                  ),
                  itemCount: controller.filteredAgents.length,
                  itemBuilder: (ctx, index) {
                    final agent = controller.filteredAgents[index];
                    return AgentCard(
                      agent: agent,
                      onTestRun: () => controller.openTestRunDrawer(agent),
                    );
                  },
                );
              },
            );
          }),
        ),
      ],
    );
  }
}
