// Field của 7 chiều onboarding cho wizard form (plan 2026-09-18 Task 4.3).
//
// Key và kiểu PHẢI khớp `services/company/operations/services/onboard-dimension-fields.ts`
// — Company từ chối field lạ. test/modules/startup_os/onboard_dimension_fields_test.dart
// đối chiếu trực tiếp với file TS. `notCaptured` không có trên form: wizard tự
// điền tên các field Founder để trống.

enum OnboardFieldKind {
  string,
  integer,
  number,
  boolean,
  stringArray,
  valueList,
  competitorList,
}

extension OnboardFieldKindWire on OnboardFieldKind {
  String get wire => switch (this) {
        OnboardFieldKind.string => 'string',
        OnboardFieldKind.integer => 'integer',
        OnboardFieldKind.number => 'number',
        OnboardFieldKind.boolean => 'boolean',
        OnboardFieldKind.stringArray => 'string_array',
        OnboardFieldKind.valueList => 'value_list',
        OnboardFieldKind.competitorList => 'competitor_list',
      };
}

class OnboardField {
  const OnboardField(this.key, this.label, this.kind, {this.options, this.hint});

  final String key;
  final String label;
  final OnboardFieldKind kind;

  /// Giá trị enum (dropdown) — key giá trị wire → nhãn hiển thị.
  final Map<String, String>? options;
  final String? hint;
}

class OnboardDimensionForm {
  const OnboardDimensionForm({
    required this.dimension,
    required this.title,
    required this.isFast,
    required this.fields,
  });

  final String dimension;
  final String title;
  final bool isFast;
  final List<OnboardField> fields;
}

const _priorityOptions = {
  '1': '1 — thấp',
  '2': '2',
  '3': '3',
  '4': '4',
  '5': '5 — cao nhất',
};

/// Thứ tự giống kịch bản hội thoại /cs:setup (Fast → Medium → Slow).
const List<OnboardDimensionForm> onboardDimensionForms = [
  OnboardDimensionForm(
    dimension: 'stage_scale',
    title: 'Giai đoạn & Quy mô',
    isFast: true,
    fields: [
      OnboardField('stage', 'Giai đoạn', OnboardFieldKind.string, options: {
        'pre_pmf': 'Chưa đạt PMF',
        'scaling': 'Đang scale',
        'optimizing': 'Tối ưu vận hành',
      }),
      OnboardField('revenueArr', 'Doanh thu năm quy đổi (ARR)', OnboardFieldKind.number),
      OnboardField('revenueCurrency', 'Đơn vị tiền tệ', OnboardFieldKind.string, hint: 'VD: VND, USD'),
      OnboardField('runwayMonths', 'Runway (tháng)', OnboardFieldKind.number),
      OnboardField('headcountFt', 'Nhân sự toàn thời gian', OnboardFieldKind.integer),
      OnboardField('headcountContractor', 'Cộng tác viên / hợp đồng', OnboardFieldKind.integer),
      OnboardField('whatBrokeLast90d', 'Điều gì đã trục trặc trong 90 ngày qua?', OnboardFieldKind.string),
    ],
  ),
  OnboardDimensionForm(
    dimension: 'challenges',
    title: 'Thách thức & Quyết định khó',
    isFast: true,
    fields: [
      OnboardField('priorityProduct', 'Ưu tiên: Sản phẩm', OnboardFieldKind.integer, options: _priorityOptions),
      OnboardField('priorityGrowth', 'Ưu tiên: Tăng trưởng', OnboardFieldKind.integer, options: _priorityOptions),
      OnboardField('priorityPeople', 'Ưu tiên: Con người', OnboardFieldKind.integer, options: _priorityOptions),
      OnboardField('priorityMoney', 'Ưu tiên: Tiền', OnboardFieldKind.integer, options: _priorityOptions),
      OnboardField('priorityOperations', 'Ưu tiên: Vận hành', OnboardFieldKind.integer, options: _priorityOptions),
      OnboardField('avoidedDecision', 'Quyết định khó đang trì hoãn', OnboardFieldKind.string),
      OnboardField('extraDayAnswer', 'Có thêm 1 ngày/tuần sẽ làm gì?', OnboardFieldKind.string),
    ],
  ),
  OnboardDimensionForm(
    dimension: 'goals_ambition',
    title: 'Mục tiêu & Tham vọng',
    isFast: false,
    fields: [
      OnboardField('goal12MonthsText', 'Mục tiêu 12 tháng', OnboardFieldKind.string),
      OnboardField('goal36MonthsText', 'Hình dung sau 36 tháng', OnboardFieldKind.string),
      OnboardField('exitOrientation', 'Định hướng dài hạn', OnboardFieldKind.string, options: {
        'exit': 'Hướng tới exit',
        'build_forever': 'Xây dựng lâu dài',
        'undecided': 'Chưa quyết định',
      }),
      OnboardField('personalSuccessDefinition', 'Thành công với cá nhân Founder là gì?', OnboardFieldKind.string),
    ],
  ),
  OnboardDimensionForm(
    dimension: 'market',
    title: 'Thị trường & Cạnh tranh',
    isFast: false,
    fields: [
      OnboardField('marketDescription', 'Mô tả thị trường & khách hàng', OnboardFieldKind.string),
      OnboardField('unfairAdvantage', 'Lợi thế không công bằng', OnboardFieldKind.string),
      OnboardField('competitiveThreat', 'Mối đe doạ cạnh tranh lớn nhất', OnboardFieldKind.string),
      OnboardField('hasRealCompetition', 'Có đối thủ cạnh tranh trực tiếp?', OnboardFieldKind.boolean),
      OnboardField('competitors', 'Đối thủ chính', OnboardFieldKind.competitorList,
          hint: 'Mỗi dòng: Tên — vì sao họ đang thắng'),
    ],
  ),
  OnboardDimensionForm(
    dimension: 'team_culture',
    title: 'Đội ngũ & Văn hoá',
    isFast: false,
    fields: [
      OnboardField('threeWords', 'Ba từ mô tả văn hoá', OnboardFieldKind.stringArray, hint: 'Cách nhau bằng dấu phẩy'),
      OnboardField('lastRealConflict', 'Xung đột thật gần nhất', OnboardFieldKind.string),
      OnboardField('conflictResolution', 'Đã giải quyết thế nào?', OnboardFieldKind.string),
      OnboardField('hasRealConflict', 'Đội có tranh luận thẳng thắn?', OnboardFieldKind.boolean),
      OnboardField('strongestLeader', 'Người dẫn dắt mạnh nhất', OnboardFieldKind.string),
      OnboardField('weakestLeader', 'Vị trí lãnh đạo đang yếu nhất', OnboardFieldKind.string),
    ],
  ),
  OnboardDimensionForm(
    dimension: 'identity',
    title: 'Căn tính & Giá trị',
    isFast: false,
    fields: [
      OnboardField('whatTheyDo', 'Startup làm gì?', OnboardFieldKind.string),
      OnboardField('whoTheyServe', 'Phục vụ ai?', OnboardFieldKind.string),
      OnboardField('foundingWhy', 'Vì sao bắt đầu?', OnboardFieldKind.string),
      OnboardField('oneSentencePitch', 'Pitch một câu', OnboardFieldKind.string),
      OnboardField('values', 'Giá trị cốt lõi', OnboardFieldKind.valueList,
          hint: 'Mỗi dòng một giá trị; thêm "!" ở đầu nếu vi phạm là lý do sa thải'),
    ],
  ),
  OnboardDimensionForm(
    dimension: 'founder',
    title: 'Hồ sơ Founder',
    isFast: false,
    fields: [
      OnboardField('founderName', 'Tên Founder (bắt buộc)', OnboardFieldKind.string),
      OnboardField('role', 'Vai trò', OnboardFieldKind.string),
      OnboardField('superpower', 'Thế mạnh vượt trội', OnboardFieldKind.string),
      OnboardField('blindSpots', 'Điểm mù tự nhận', OnboardFieldKind.string),
      OnboardField('archetype', 'Kiểu Founder', OnboardFieldKind.string, options: {
        'product': 'Sản phẩm',
        'sales': 'Bán hàng',
        'technical': 'Kỹ thuật',
        'operator': 'Vận hành',
        'hybrid': 'Lai',
      }),
      OnboardField('whatKeepsUp', 'Điều gì khiến mất ngủ?', OnboardFieldKind.string),
      OnboardField('cofounderCritique', 'Co-founder hay phê bình điều gì?', OnboardFieldKind.string),
    ],
  ),
];

String dimensionTitle(String dimension) => onboardDimensionForms
    .firstWhere(
      (f) => f.dimension == dimension,
      orElse: () => OnboardDimensionForm(dimension: dimension, title: dimension, isFast: false, fields: const []),
    )
    .title;

/// Chuyển giá trị form (chuỗi người dùng nhập) thành payload đúng kiểu Company.
///
/// Trả về null khi không có field nào được điền. Field để trống được liệt kê
/// trong `notCaptured` thay vì gửi giá trị rỗng/giả. Ném [FormatException] khi
/// giá trị số không hợp lệ để form báo lỗi tại chỗ.
Map<String, Object>? buildDimensionPayload(OnboardDimensionForm form, Map<String, String> raw) {
  final data = <String, Object>{};
  final notCaptured = <String>[];

  for (final field in form.fields) {
    final text = (raw[field.key] ?? '').trim();
    if (text.isEmpty) {
      notCaptured.add(field.key);
      continue;
    }
    switch (field.kind) {
      case OnboardFieldKind.string:
        data[field.key] = text;
      case OnboardFieldKind.integer:
        final value = int.tryParse(text);
        if (value == null || value < 0) {
          throw FormatException('${field.label}: cần số nguyên không âm');
        }
        data[field.key] = value;
      case OnboardFieldKind.number:
        final value = double.tryParse(text.replaceAll(',', '.'));
        if (value == null || value < 0 || !value.isFinite) {
          throw FormatException('${field.label}: cần số không âm');
        }
        data[field.key] = value;
      case OnboardFieldKind.boolean:
        data[field.key] = text == 'true';
      case OnboardFieldKind.stringArray:
        data[field.key] =
            text.split(',').map((s) => s.trim()).where((s) => s.isNotEmpty).toList(growable: false);
      case OnboardFieldKind.valueList:
        data[field.key] = text
            .split('\n')
            .map((line) => line.trim())
            .where((line) => line.isNotEmpty)
            .map((line) => line.startsWith('!')
                ? {'valueText': line.substring(1).trim(), 'isFireWorthy': true}
                : {'valueText': line, 'isFireWorthy': false})
            .where((v) => (v['valueText'] as String).isNotEmpty)
            .toList(growable: false);
      case OnboardFieldKind.competitorList:
        data[field.key] = text
            .split('\n')
            .map((line) => line.trim())
            .where((line) => line.isNotEmpty)
            .map((line) {
              final parts = line.split(RegExp(r'\s+[—-]\s+'));
              final name = parts.first.trim();
              final why = parts.length > 1 ? parts.sublist(1).join(' - ').trim() : '';
              return <String, String>{'name': name, if (why.isNotEmpty) 'whyWinning': why};
            })
            .toList(growable: false);
    }
  }

  if (data.isEmpty) return null;
  if (form.dimension == 'founder' && !data.containsKey('founderName')) {
    throw const FormatException('Tên Founder là bắt buộc');
  }
  if (notCaptured.isNotEmpty) data['notCaptured'] = notCaptured;
  return data;
}
