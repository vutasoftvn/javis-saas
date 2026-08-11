import os

def generate_module(module_name, class_prefix):
    base_dir = f"frontend/lib/modules/{module_name}"
    os.makedirs(f"{base_dir}/bindings", exist_ok=True)
    os.makedirs(f"{base_dir}/controllers", exist_ok=True)
    os.makedirs(f"{base_dir}/views", exist_ok=True)

    with open(f"{base_dir}/bindings/{module_name}_binding.dart", "w") as f:
        f.write(f"""import 'package:get/get.dart';
import '../controllers/{module_name}_controller.dart';

class {class_prefix}Binding extends Bindings {{
  @override
  void dependencies() {{
    Get.lazyPut<{class_prefix}Controller>(
      () => {class_prefix}Controller(),
    );
  }}
}}
""")

    with open(f"{base_dir}/controllers/{module_name}_controller.dart", "w") as f:
        f.write(f"""import 'package:get/get.dart';

class {class_prefix}Controller extends GetxController {{
  final isLoading = false.obs;

  @override
  void onInit() {{
    super.onInit();
    loadData();
  }}

  Future<void> loadData() async {{
    isLoading.value = true;
    try {{
      // Load data
    }} finally {{
      isLoading.value = false;
    }}
  }}
}}
""")

    with open(f"{base_dir}/views/{module_name}_view.dart", "w") as f:
        f.write(f"""import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/{module_name}_controller.dart';

class {class_prefix}View extends GetView<{class_prefix}Controller> {{
  const {class_prefix}View({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('{class_prefix}'),
      ),
      body: Obx(() {{
        if (controller.isLoading.value) {{
          return const Center(child: CircularProgressIndicator());
        }}
        return const Center(
          child: Text('{class_prefix} View is working'),
        );
      }}),
    );
  }}
}}
""")

generate_module("connections", "Connections")
generate_module("plugins", "Plugins")
generate_module("audit", "Audit")
