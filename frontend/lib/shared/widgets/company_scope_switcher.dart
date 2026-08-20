import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:frontend/core/controllers/company_scope_controller.dart';

class CompanyScopeSwitcher extends StatelessWidget {
  const CompanyScopeSwitcher({super.key});

  @override
  Widget build(BuildContext context) {
    // Ensure controller is registered if not already
    final controller = Get.isRegistered<CompanyScopeController>()
        ? Get.find<CompanyScopeController>()
        : Get.put(CompanyScopeController());

    return Obx(() {
      final isGlobal = controller.isGlobalScope;
      final label = isGlobal ? 'Toàn công ty' : 'Phạm vi hẹp';

      return InkWell(
        onTap: () {
          // Future: Open a dialog or dropdown to select scope
          if (isGlobal) {
            controller.setScope(operatingUnitId: 201, offeringId: 301);
          } else {
            controller.clearScope();
          }
        },
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isGlobal ? Icons.business : Icons.filter_alt,
                size: 16,
                color: Colors.white70,
              ),
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(width: 4),
              const Icon(
                Icons.arrow_drop_down,
                size: 18,
                color: Colors.white54,
              ),
            ],
          ),
        ),
      );
    });
  }
}
