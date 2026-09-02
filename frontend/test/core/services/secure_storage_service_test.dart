import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes/fake_secret_store.dart';

const _secureStorageChannel = MethodChannel(
  'plugins.it_nomads.com/flutter_secure_storage',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('real MethodChannel failure (Keychain/Keystore lỗi native)', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
      // `test/flutter_test_config.dart` đặt sẵn một FakeSecretStore mặc định
      // cho toàn bộ suite (để các test khác không cần biết gì về
      // flutter_secure_storage) — nhóm test này cố tình cần MethodChannel
      // thật nên phải khôi phục FlutterSecureSecretStore ở đây.
      SecureStorageService.resetForTest();
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
  });

  group('SecretStore test double (configureForTest — no MethodChannel needed)', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    tearDown(() {
      SecureStorageService.resetForTest();
    });

    test(
      'secret write propagates a Keychain failure and leaves preferences empty',
      () async {
        SecureStorageService.configureForTest(const ThrowingSecretStore());
        await expectLater(
          SecureStorageService.write(
            SecureStorageService.localSessionTokenKey,
            'jwt',
          ),
          throwsA(isA<PlatformException>()),
        );
        expect(
          (await SharedPreferences.getInstance()).containsKey(
            SecureStorageService.localSessionTokenKey,
          ),
          isFalse,
        );
      },
    );

    test('secret read propagates a Keychain failure', () async {
      SecureStorageService.configureForTest(const ThrowingSecretStore());
      await expectLater(
        SecureStorageService.read(SecureStorageService.platformAccessTokenKey),
        throwsA(isA<PlatformException>()),
      );
    });

    test('secret delete propagates a Keychain failure', () async {
      SecureStorageService.configureForTest(const ThrowingSecretStore());
      await expectLater(
        SecureStorageService.delete('auth_token'),
        throwsA(isA<PlatformException>()),
      );
    });

    test(
      'migrate propagates a Keychain failure and keeps the legacy plaintext copy '
      '(never delete-then-write)',
      () async {
        SharedPreferences.setMockInitialValues({
          'local_session_token': 'legacy-jwt',
        });
        SecureStorageService.configureForTest(const ThrowingSecretStore());

        await expectLater(
          SecureStorageService.migrateFromSharedPreferences(),
          throwsA(isA<PlatformException>()),
        );

        final prefs = await SharedPreferences.getInstance();
        expect(prefs.getString('local_session_token'), 'legacy-jwt');
      },
    );

    test(
      'migrate deletes the legacy plaintext copy only after a successful secure write',
      () async {
        SharedPreferences.setMockInitialValues({
          'local_session_token': 'legacy-jwt',
        });
        final fake = FakeSecretStore();
        SecureStorageService.configureForTest(fake);

        await SecureStorageService.migrateFromSharedPreferences();

        final prefs = await SharedPreferences.getInstance();
        expect(prefs.getString('local_session_token'), isNull);
        expect(await fake.read('local_session_token'), 'legacy-jwt');
      },
    );

    test(
      'a fake in-memory SecretStore lets a widget test round-trip a secret '
      'without a MethodChannel or the old widget-test heuristic',
      () async {
        final fake = FakeSecretStore();
        SecureStorageService.configureForTest(fake);

        await SecureStorageService.write('auth_token', 'fake-token');

        expect(await SecureStorageService.read('auth_token'), 'fake-token');
        // Không rơi xuống SharedPreferences — chứng minh route đi thẳng qua
        // SecretStore đã cấu hình, không qua heuristic cũ.
        expect(
          (await SharedPreferences.getInstance()).containsKey('auth_token'),
          isFalse,
        );

        await SecureStorageService.delete('auth_token');
        expect(await SecureStorageService.read('auth_token'), isNull);
      },
    );

    test(
      'non-secret keys (workspace_id/role) go through the plain '
      'SharedPreferences cache store, not the fail-closed secret store',
      () async {
        // Không dùng ThrowingSecretStore ở đây: đây chính là điểm khác biệt
        // cần chứng minh — workspace_id/role không đi qua _secretStore nên
        // một secret store luôn ném lỗi không ảnh hưởng đến chúng.
        SecureStorageService.configureForTest(const ThrowingSecretStore());

        await SecureStorageService.write('workspace_id', 'ws-1');

        final prefs = await SharedPreferences.getInstance();
        expect(prefs.getString('workspace_id'), 'ws-1');
        expect(await SecureStorageService.read('workspace_id'), 'ws-1');
      },
    );
  });
}
