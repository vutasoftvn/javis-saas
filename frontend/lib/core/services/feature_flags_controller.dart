import 'package:get/get.dart';

import '../../core/services/feature_flags_service.dart';

abstract class FeatureFlagsLoader {
  Future<Map<String, bool>> load();
}

class ApiFeatureFlagsLoader implements FeatureFlagsLoader {
  ApiFeatureFlagsLoader([FeatureFlagsService? service])
      : _service = service ?? FeatureFlagsService();

  final FeatureFlagsService _service;

  @override
  Future<Map<String, bool>> load() => _service.load();
}

class FeatureFlagsController extends GetxController {
  FeatureFlagsController({FeatureFlagsLoader? loader})
      : _loader = loader ?? ApiFeatureFlagsLoader();

  final FeatureFlagsLoader _loader;
  final flags = <String, bool>{}.obs;
  final loaded = false.obs;

  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    flags.assignAll(await _loader.load());
    loaded.value = true;
  }

  bool isEnabled(String key) => flags[key] == true;
}
