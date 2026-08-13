import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/sales_service.dart';

class CustomerController extends GetxController {
  final isLoading = false.obs;
  final customers = <dynamic>[].obs;

  @override
  void onInit() {
    super.onInit();
    loadCustomers();
  }

  Future<void> loadCustomers() async {
    isLoading.value = true;
    try {
      final list = await SalesService().getCustomers();
      customers.assignAll(list);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> updateHealth(String customerId, String health) async {
    final res = await SalesService().updateCustomerHealth(customerId, health);
    if (res != null) {
      await loadCustomers();
    }
  }
}

class CustomerView extends StatelessWidget {
  const CustomerView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<CustomerController>()) {
      Get.put(CustomerController());
    }
    final c = Get.find<CustomerController>();

    return Obx(() {
      if (c.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }

      return ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Danh sách khách hàng', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
              IconButton(icon: const Icon(Icons.refresh), onPressed: c.loadCustomers),
            ],
          ),
          const SizedBox(height: 12),
          if (c.customers.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Center(
                  child: Text('Không tìm thấy khách hàng nào', style: TextStyle(color: Colors.grey.shade600)),
                ),
              ),
            )
          else
            ...c.customers.map((cust) {
              final id = cust['id'] as String;
              final health = cust['health_status'] ?? 'HEALTHY';
              final life = cust['lifecycle_status'] ?? 'ONBOARDING';

              Color healthColor = Colors.green;
              if (health == 'WATCH') healthColor = Colors.orange;
              if (health == 'AT_RISK') healthColor = Colors.red;

              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text('Khách hàng #$id', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('Vòng đời: $life • Sức khỏe: $health'),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: healthColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: healthColor),
                    ),
                    child: Text(health, style: TextStyle(color: healthColor, fontWeight: FontWeight.bold, fontSize: 11)),
                  ),
                ),
              );
            }),
        ],
      );
    });
  }
}
