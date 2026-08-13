import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/foundation_controller.dart';
import 'tabs/foundation_tab.dart';
import '../../../core/widgets/floating_app_bar.dart';

class StrategyFoundationView extends GetView<FoundationController> {
  const StrategyFoundationView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FoundationController>()) {
      Get.put(FoundationController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: const [
          JavisFloatingAppBar(
            title: 'Chiến lược Doanh nghiệp (Vision, Mission, Values)',
            subtitle: 'Khởi tạo và quản trị khung chiến lược với 1 Vision, 1 Mission và 3 Core Values cốt lõi.',
          ),
          Expanded(
            child: FoundationTab(),
          ),
        ],
      ),
    );
  }
}
