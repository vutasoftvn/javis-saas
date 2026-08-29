import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/vault_controller.dart';

class VaultKnowledgeStudioPanel extends StatelessWidget {
  final VaultController controller;

  const VaultKnowledgeStudioPanel({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (!controller.showKnowledgeStudio.value) {
        return const SizedBox.shrink();
      }

      return Container(
        margin: const EdgeInsets.fromLTRB(10, 0, 10, 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFF0B1220),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.auto_awesome_rounded, size: 13, color: Color(0xFF00F0FF)),
                const SizedBox(width: 6),
                const Text(
                  'Knowledge Objects',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const Spacer(),
                Text(
                  '${controller.knowledgeObjects.length} mục',
                  style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: [
                _filterChip('Tất cả', controller.selectedKnowledgeType.value.isEmpty, () {
                  controller.selectedKnowledgeType.value = '';
                  controller.loadKnowledgeObjects();
                }),
                ...['note', 'research', 'decision', 'concept'].map((t) => _filterChip(
                      t,
                      controller.selectedKnowledgeType.value == t,
                      () {
                        controller.selectedKnowledgeType.value = t;
                        controller.loadKnowledgeObjects();
                      },
                    )),
              ],
            ),
          ],
        ),
      );
    });
  }

  Widget _filterChip(String label, bool selected, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF00F0FF).withValues(alpha: 0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? const Color(0xFF00F0FF) : const Color(0xFF1E293B),
            width: 0.8,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 9.5,
            color: selected ? Colors.white : const Color(0xFF94A3B8),
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }
}
