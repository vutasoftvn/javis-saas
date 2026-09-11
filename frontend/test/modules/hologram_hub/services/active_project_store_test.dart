import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/hologram_hub/services/active_project_store.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.resetForTest();
  });

  tearDown(() {
    SecureStorageService.resetForTest();
  });

  group('ActiveProjectStore', () {
    test('write persists project ID with workspace namespace', () async {
      await ActiveProjectStore.write('ws_1', 'proj_b');
      final stored = await ActiveProjectStore.read('ws_1');
      expect(stored, 'proj_b');
    });

    test('read returns null when key does not exist', () async {
      final stored = await ActiveProjectStore.read('ws_1');
      expect(stored, isNull);
    });

    test('different workspaces have separate keys', () async {
      await ActiveProjectStore.write('ws_1', 'proj_a');
      await ActiveProjectStore.write('ws_2', 'proj_b');

      final ws1 = await ActiveProjectStore.read('ws_1');
      final ws2 = await ActiveProjectStore.read('ws_2');

      expect(ws1, 'proj_a');
      expect(ws2, 'proj_b');
    });

    test('delete removes the stored project ID', () async {
      await ActiveProjectStore.write('ws_1', 'proj_a');
      await ActiveProjectStore.delete('ws_1');

      final stored = await ActiveProjectStore.read('ws_1');
      expect(stored, isNull);
    });

    test('write overwrites previous value for same workspace', () async {
      await ActiveProjectStore.write('ws_1', 'proj_a');
      await ActiveProjectStore.write('ws_1', 'proj_b');

      final stored = await ActiveProjectStore.read('ws_1');
      expect(stored, 'proj_b');
    });
  });
}
