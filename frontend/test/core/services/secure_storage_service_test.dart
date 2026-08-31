import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _secureStorageChannel = MethodChannel(
  'plugins.it_nomads.com/flutter_secure_storage',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureStorageChannel, (methodCall) async {
          throw PlatformException(
            code: 'keychain_error',
            message: 'Keychain is unavailable',
          );
        });
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureStorageChannel, null);
  });

  test(
    'does not persist a token in SharedPreferences after a Keychain write failure',
    () async {
      await expectLater(
        SecureStorageService.write('auth_token', 'sensitive-token'),
        throwsA(isA<PlatformException>()),
      );

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('auth_token'), isNull);
    },
  );

  test('does not read a legacy token after a Keychain read failure', () async {
    SharedPreferences.setMockInitialValues({'auth_token': 'legacy-token'});

    await expectLater(
      SecureStorageService.read('auth_token'),
      throwsA(isA<PlatformException>()),
    );
  });

  test(
    'does not delete a legacy token after a Keychain delete failure',
    () async {
      SharedPreferences.setMockInitialValues({'auth_token': 'legacy-token'});

      await expectLater(
        SecureStorageService.delete('auth_token'),
        throwsA(isA<PlatformException>()),
      );

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('auth_token'), 'legacy-token');
    },
  );
}
