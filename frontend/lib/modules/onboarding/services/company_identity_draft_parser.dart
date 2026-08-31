/// Kết quả parse câu trả lời tự do của AI thành 3 khối Vision/Mission/Values.
/// Field null nghĩa là AI không trả lời đúng định dạng — caller (modal) tự
/// quyết định fallback (đổ nguyên văn vào ô Vision), parser không tự đoán.
class CompanyIdentityDraft {
  const CompanyIdentityDraft({this.vision, this.mission, this.coreValues});

  final String? vision;
  final String? mission;
  final String? coreValues;

  bool get isComplete =>
      (vision?.trim().isNotEmpty ?? false) &&
      (mission?.trim().isNotEmpty ?? false) &&
      (coreValues?.trim().isNotEmpty ?? false);
}

String? _extractSection(String text, String label, List<String> nextLabels) {
  final labelMatch = RegExp('$label\\s*:', caseSensitive: false).firstMatch(text);
  if (labelMatch == null) return null;

  var end = text.length;
  for (final next in nextLabels) {
    final nextMatch =
        RegExp('$next\\s*:', caseSensitive: false).firstMatch(text.substring(labelMatch.end));
    if (nextMatch != null) {
      final absoluteStart = labelMatch.end + nextMatch.start;
      if (absoluteStart < end) end = absoluteStart;
    }
  }
  final section = text.substring(labelMatch.end, end).trim();
  return section.isEmpty ? null : section;
}

/// Kỳ vọng AI trả lời đúng 3 dòng `VISION:`/`MISSION:`/`VALUES:` (prompt gửi
/// đi ở Task 8 yêu cầu định dạng này rõ ràng). Không phụ thuộc thứ tự các
/// khối còn lại khi cắt biên mỗi section, chỉ cần đúng nhãn xuất hiện.
CompanyIdentityDraft parseCompanyIdentityDraft(String text) {
  return CompanyIdentityDraft(
    vision: _extractSection(text, 'VISION', ['MISSION', 'VALUES']),
    mission: _extractSection(text, 'MISSION', ['VALUES']),
    coreValues: _extractSection(text, 'VALUES', []),
  );
}
