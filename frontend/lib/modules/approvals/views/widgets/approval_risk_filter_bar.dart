import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/approvals_controller.dart';

class ApprovalRiskFilterBar extends StatelessWidget {
  final ApprovalsController controller;

  const ApprovalRiskFilterBar({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
      ),
      child: Row(
        children: [
          const Text('Mức rủi ro:', style: TextStyle(color: Colors.grey, fontSize: 12.5, fontWeight: FontWeight.w600)),
          const SizedBox(width: 12),
          _buildRiskFilterChip('Tất cả', 'ALL'),
          const SizedBox(width: 8),
          _buildRiskFilterChip('🔴 CRITICAL (Founder Only)', 'CRITICAL', color: const Color(0xFFEF4444)),
          const SizedBox(width: 8),
          _buildRiskFilterChip('🟠 HIGH RISK (Lead Review)', 'HIGH', color: const Color(0xFFF59E0B)),
        ],
      ),
    );
  }

  Widget _buildRiskFilterChip(String label, String value, {Color? color}) {
    return Obx(() {
      final isSelected = controller.selectedRiskFilter.value == value;
      return FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) => controller.setRiskFilter(value),
        selectedColor: color ?? Colors.blueAccent,
        backgroundColor: const Color(0xFF1E293B),
        labelStyle: TextStyle(
          fontSize: 12,
          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
          color: isSelected ? Colors.white : Colors.grey.shade400,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(
            color: isSelected ? (color ?? Colors.blueAccent) : const Color(0xFF334155),
          ),
        ),
      );
    });
  }
}
