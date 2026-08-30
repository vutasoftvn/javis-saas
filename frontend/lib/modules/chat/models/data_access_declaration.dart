import 'package:flutter/foundation.dart';

/// Danh mục truy cập dữ liệu hợp lệ — PHẢI khớp đúng 4 giá trị business
/// logic thật dùng ở phía Company (services/company). Không cho phép người
/// dùng tự gõ giá trị tự do vì Pydantic phía backend không có enum
/// whitelist — ràng buộc này phải nằm ở phía client (Flutter) thay.
enum DataAccessCategory {
  nonPersonal('NON_PERSONAL', 'Non-personal'),
  personal('PERSONAL', 'Personal'),
  sensitivePersonal('SENSITIVE_PERSONAL', 'Sensitive personal'),
  businessConfidential('BUSINESS_CONFIDENTIAL', 'Business confidential');

  const DataAccessCategory(this.apiValue, this.label);

  /// Giá trị gửi lên API (khớp đúng string enum phía backend/Company).
  final String apiValue;

  /// Nhãn hiển thị trên UI (chip).
  final String label;
}

/// Khai báo phân loại dữ liệu (data access classification) mà người dùng
/// PHẢI cung cấp trước khi gửi tin nhắn trực tiếp tới model — khớp field
/// `data_access` bắt buộc của API tạo message (Task 5).
///
/// Bất biến (immutable): mọi thay đổi phải tạo instance mới qua
/// [copyWith] — tránh side effect ẩn khi truyền declaration qua nhiều lớp
/// (controller -> service -> API).
@immutable
class DataAccessDeclaration {
  const DataAccessDeclaration({
    this.categories = const <DataAccessCategory>{},
    this.subjectReference,
  });

  final Set<DataAccessCategory> categories;
  final String? subjectReference;

  /// Danh mục nào bắt buộc phải có subject_reference không rỗng — khớp
  /// validate phía server ở Task 5 (PERSONAL / SENSITIVE_PERSONAL).
  static const Set<DataAccessCategory> _categoriesRequiringSubject = {
    DataAccessCategory.personal,
    DataAccessCategory.sensitivePersonal,
  };

  bool get requiresSubjectReference =>
      categories.any(_categoriesRequiringSubject.contains);

  bool get hasSubjectReference =>
      subjectReference != null && subjectReference!.trim().isNotEmpty;

  /// Hợp lệ để cho phép bấm Send: phải chọn ít nhất 1 category, và nếu
  /// category yêu cầu subject_reference thì phải nhập không rỗng.
  bool get isValid =>
      categories.isNotEmpty && (!requiresSubjectReference || hasSubjectReference);

  DataAccessDeclaration copyWith({
    Set<DataAccessCategory>? categories,
    String? subjectReference,
    bool clearSubjectReference = false,
  }) {
    return DataAccessDeclaration(
      categories: categories ?? this.categories,
      subjectReference:
          clearSubjectReference ? null : (subjectReference ?? this.subjectReference),
    );
  }

  /// Serialize đúng shape API mong đợi:
  /// `{"categories": [...], "subject_reference": ...}`.
  Map<String, dynamic> toJson() => {
        'categories': categories.map((c) => c.apiValue).toList(),
        'subject_reference': subjectReference,
      };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DataAccessDeclaration &&
          runtimeType == other.runtimeType &&
          setEquals(categories, other.categories) &&
          subjectReference == other.subjectReference;

  @override
  int get hashCode => Object.hash(Object.hashAllUnordered(categories), subjectReference);
}
