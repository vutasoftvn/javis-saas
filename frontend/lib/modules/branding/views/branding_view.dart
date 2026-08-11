import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/branding_controller.dart';

class BrandingView extends GetView<BrandingController> {
  const BrandingView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Branding'),
      ),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }
        return const Center(
          child: Text('Branding View is working'),
        );
      }),
    );
  }
}
