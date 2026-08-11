import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';

class GraphController extends GetxController {
  final nodes = <String>['Home', 'Strategy', 'Vault', 'Tasks'].obs;
}

class GraphViewPage extends GetView<GraphController> {
  const GraphViewPage({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<GraphController>()) {
      Get.put(GraphController());
    }

    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      appBar: AppBar(
        title: const Text('Knowledge Graph'),
        backgroundColor: Colors.transparent,
      ),
      body: Center(
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
          ),
          child: const Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.hub_rounded, color: AppTheme.primaryLight, size: 48),
              SizedBox(height: 16),
              Text(
                'Knowledge Graph Interactive View',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              SizedBox(height: 8),
              Text(
                'Trực quan hóa cấu trúc liên kết tri thức giữa các tài liệu Vault và Chiến lược.',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
