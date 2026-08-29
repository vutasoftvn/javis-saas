// M0 contract freeze — round-trip enum canonical + UUIDv7 contract.
// Nguồn: shared/contracts/enums.json · Xem M0-contract-freeze.md §Test plan.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/contracts/enums.generated.dart';

Map<String, dynamic> _readJson(String relFromRepoRoot) {
  // `flutter test` chạy với cwd = frontend/ ; repo root là thư mục cha.
  final f = File('../$relFromRepoRoot');
  return jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
}

void main() {
  final src = _readJson('shared/contracts/enums.json');
  final idFixtures = _readJson('shared/contracts/fixtures/id-samples.json');
  final srcEnums = src['enums'] as Map<String, dynamic>;

  List<String> values(String name) =>
      (srcEnums[name]['values'] as List).cast<String>();

  final cases = <String, ({List<String> wires, String Function(String) parse})>{
    'workspace_lifecycle_stage': (
      wires: WorkspaceLifecycleStage.values.map((e) => e.wire).toList(),
      parse: (v) => WorkspaceLifecycleStage.fromWire(v).toApi(),
    ),
    'project_lifecycle_stage': (
      wires: ProjectLifecycleStage.values.map((e) => e.wire).toList(),
      parse: (v) => ProjectLifecycleStage.fromWire(v).toApi(),
    ),
    'workspace_status': (
      wires: WorkspaceStatus.values.map((e) => e.wire).toList(),
      parse: (v) => WorkspaceStatus.fromWire(v).toApi(),
    ),
    'project_status': (
      wires: ProjectStatus.values.map((e) => e.wire).toList(),
      parse: (v) => ProjectStatus.fromWire(v).toApi(),
    ),
    'runtime_mode': (
      wires: RuntimeMode.values.map((e) => e.wire).toList(),
      parse: (v) => RuntimeMode.fromWire(v).toApi(),
    ),
    'sync_policy': (
      wires: SyncPolicy.values.map((e) => e.wire).toList(),
      parse: (v) => SyncPolicy.fromWire(v).toApi(),
    ),
    'sync_status': (
      wires: SyncStatus.values.map((e) => e.wire).toList(),
      parse: (v) => SyncStatus.fromWire(v).toApi(),
    ),
    'legal_entity_status': (
      wires: LegalEntityStatus.values.map((e) => e.wire).toList(),
      parse: (v) => LegalEntityStatus.fromWire(v).toApi(),
    ),
  };

  group('workspace-canonical enums (generated dart)', () {
    cases.forEach((name, c) {
      test('$name: khớp thứ tự value nguồn', () {
        expect(c.wires, equals(values(name)));
      });
      test('$name: round-trip mọi value', () {
        for (final v in values(name)) {
          expect(c.parse(v), equals(v));
        }
      });
      test('$name: value lạ -> throw, không map ngầm', () {
        expect(() => c.parse('__NOT_REAL__'), throwsArgumentError);
      });
    });

    test('tryFromWire trả null cho value lạ (không default ngầm)', () {
      expect(WorkspaceLifecycleStage.tryFromWire('S0_GENESIS'), isNull);
      expect(ProjectLifecycleStage.tryFromWire('S0_EXPLORE'), isNull);
    });

    test('stage enum không lẫn mã legacy S*', () {
      expect(
        WorkspaceLifecycleStage.values.every((e) => e.wire.startsWith('W')),
        isTrue,
      );
      expect(
        ProjectLifecycleStage.values.every((e) => e.wire.startsWith('P')),
        isTrue,
      );
    });

    test('migration map phủ đủ target canonical', () {
      expect(
        legacyWorkspaceStageToCanonical.values.toSet(),
        equals(WorkspaceLifecycleStage.values.map((e) => e.wire).toSet()),
      );
      expect(
        legacyProjectStageToCanonical.values.toSet(),
        equals(ProjectLifecycleStage.values.map((e) => e.wire).toSet()),
      );
    });
  });

  group('ID serialization contract (M0)', () {
    test('Snowflake decimal string round-trip qua BigInt, không mất precision', () {
      final samples = (idFixtures['snowflake_decimal_strings']['samples'] as List)
          .cast<String>();
      for (final s in samples) {
        final decoded =
            jsonDecode(jsonEncode({'workspace_id': s})) as Map<String, dynamic>;
        expect(decoded['workspace_id'], isA<String>());
        expect(BigInt.parse(decoded['workspace_id'] as String).toString(), equals(s));
      }
    });

    test('giá trị 63-bit vỡ nếu ép qua double', () {
      final risky = (idFixtures['snowflake_decimal_strings']
              ['must_not_equal_after_double_roundtrip'] as List)
          .cast<String>();
      for (final s in risky) {
        final asDouble = double.parse(s);
        expect(asDouble.toStringAsFixed(0) == s, isFalse);
        expect(BigInt.parse(s).toString(), equals(s));
      }
    });

    test('UUIDv7 fixtures: version 7 + variant 10xx + canonical', () {
      final re = RegExp(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
      );
      for (final s in (idFixtures['uuidv7']['ordered_samples'] as List).cast<String>()) {
        expect(re.hasMatch(s), isTrue, reason: s);
      }
      for (final s in (idFixtures['uuidv7']['not_v7'] as List).cast<String>()) {
        expect(re.hasMatch(s), isFalse, reason: s);
      }
    });

    test('UUIDv7 đơn điệu thời gian = sắp xếp lexicographic', () {
      final ordered =
          (idFixtures['uuidv7']['ordered_samples'] as List).cast<String>();
      final sorted = [...ordered]..sort();
      expect(sorted, equals(ordered));
    });
  });
}
