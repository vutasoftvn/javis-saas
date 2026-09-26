import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/startup_os/models/onboard_dimension_fields.dart';
import 'package:frontend/modules/startup_os/widgets/onboard_wizard_dialog.dart';

// Field form wizard phải khớp đúng bảng field Company lưu
// (services/company/operations/services/onboard-dimension-fields.ts) — Company
// từ chối field lạ, nên lệch key làm form không bao giờ lưu được.

Map<String, Map<String, String>> _companyFieldTable() {
  final source = File(
    '../services/company/operations/services/onboard-dimension-fields.ts',
  ).readAsStringSync();
  final block = RegExp(
    r'export const ONBOARD_DIMENSION_FIELDS = \{(.*?)\n\} as const',
    dotAll: true,
  ).firstMatch(source)!.group(1)!;
  final table = <String, Map<String, String>>{};
  for (final dim in RegExp(
    r'\n  (\w+): \{(.*?)\n  \},',
    dotAll: true,
  ).allMatches(block)) {
    table[dim.group(1)!] = {
      for (final f in RegExp(r'(\w+): "(\w+)"').allMatches(dim.group(2)!))
        f.group(1)!: f.group(2)!,
    };
  }
  return table;
}

OnboardDimensionForm _form(String dimension) =>
    onboardDimensionForms.firstWhere((f) => f.dimension == dimension);

void main() {
  test(
    'wizard covers every Company dimension with matching field keys and kinds',
    () {
      final company = _companyFieldTable();
      expect(
        onboardDimensionForms.map((f) => f.dimension).toSet(),
        company.keys.toSet(),
      );
      for (final form in onboardDimensionForms) {
        final expected = Map.of(company[form.dimension]!)
          ..remove('notCaptured');
        expect(
          {for (final f in form.fields) f.key: f.kind.wire},
          expected,
          reason: form.dimension,
        );
      }
    },
  );

  test('only stage_scale and challenges are fast dimensions', () {
    expect(
      onboardDimensionForms.where((f) => f.isFast).map((f) => f.dimension),
      ['stage_scale', 'challenges'],
    );
  });

  test('builds typed payload and lists skipped fields in notCaptured', () {
    final payload = buildDimensionPayload(_form('stage_scale'), {
      'stage': 'pre_pmf',
      'revenueArr': '150000,5',
      'headcountFt': '4',
    })!;
    expect(payload['stage'], 'pre_pmf');
    expect(payload['revenueArr'], 150000.5);
    expect(payload['headcountFt'], 4);
    expect(
      payload['notCaptured'],
      containsAll(['runwayMonths', 'whatBrokeLast90d']),
    );
    expect(payload.containsKey('runwayMonths'), isFalse);
  });

  test('returns null when nothing was filled', () {
    expect(buildDimensionPayload(_form('challenges'), const {}), isNull);
  });

  test('rejects invalid numbers and a founder without a name', () {
    expect(
      () => buildDimensionPayload(_form('stage_scale'), {'headcountFt': 'bốn'}),
      throwsFormatException,
    );
    expect(
      () => buildDimensionPayload(_form('founder'), {'superpower': 'Bán hàng'}),
      throwsFormatException,
    );
  });

  test('parses values, competitors, arrays and booleans', () {
    final identity = buildDimensionPayload(_form('identity'), {
      'values': '!Khách hàng trước\nMinh bạch\n',
    })!;
    expect(identity['values'], [
      {'valueText': 'Khách hàng trước', 'isFireWorthy': true},
      {'valueText': 'Minh bạch', 'isFireWorthy': false},
    ]);

    final market = buildDimensionPayload(_form('market'), {
      'competitors': 'MISA — giá rẻ\nFast',
      'hasRealCompetition': 'true',
    })!;
    expect(market['competitors'], [
      {'name': 'MISA', 'whyWinning': 'giá rẻ'},
      {'name': 'Fast'},
    ]);
    expect(market['hasRealCompetition'], isTrue);

    final team = buildDimensionPayload(_form('team_culture'), {
      'threeWords': 'nhanh, thẳng thắn , ',
    })!;
    expect(team['threeWords'], ['nhanh', 'thẳng thắn']);
  });

  test('prefills the form from the current Company context', () {
    final context = {
      'stage_scale': {
        'id': '1',
        'stage': 'scaling',
        'revenueArr': '120000.00',
        'headcountFt': 9,
      },
      'identity': {
        'whatTheyDo': 'Kế toán AI',
        'values': [
          {'valueText': 'Khách hàng trước', 'isFireWorthy': true},
        ],
      },
      'founders': [
        {'founderName': 'Lan', 'archetype': 'sales'},
      ],
      'market': null,
    };
    expect(prefillFromContext(_form('stage_scale'), context), {
      'stage': 'scaling',
      'revenueArr': '120000.00',
      'headcountFt': '9',
    });
    expect(prefillFromContext(_form('identity'), context), {
      'whatTheyDo': 'Kế toán AI',
      'values': '!Khách hàng trước',
    });
    expect(prefillFromContext(_form('founder'), context), {
      'founderName': 'Lan',
      'archetype': 'sales',
    });
    expect(prefillFromContext(_form('market'), context), isEmpty);
  });
}
