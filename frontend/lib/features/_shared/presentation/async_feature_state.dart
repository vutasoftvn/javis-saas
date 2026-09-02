import 'package:frontend/core/network/api_result.dart';

sealed class AsyncFeatureState<T> {
  const AsyncFeatureState();
}

final class FeatureInitial<T> extends AsyncFeatureState<T> {
  const FeatureInitial();
}

final class FeatureLoading<T> extends AsyncFeatureState<T> {
  const FeatureLoading();
}

/// Task 6 — một collection thành công nhưng THẬT SỰ rỗng (200 + `[]`) vẫn là
/// [FeatureData] với `value` rỗng, KHÔNG cần một variant `FeatureEmpty` riêng:
/// "đã tải xong, không có gì" và "chưa tải xong/tải lỗi" là hai khái niệm
/// khác nhau và đã được `AsyncFeatureState` phân biệt rạch ròi bằng loại biến
/// thể (`FeatureData` vs `FeatureFailure`/`FeatureLoading`), không phải bằng
/// nội dung của `value`. Thêm `FeatureEmpty` sẽ tạo một model song song không
/// cần thiết — xem `FeatureStateView` (features/_shared/presentation) nơi
/// UI tự quyết định hiển thị "rỗng" dựa trên `value.isEmpty` bên trong nhánh
/// `FeatureData`.
final class FeatureData<T> extends AsyncFeatureState<T> {
  const FeatureData(this.value, this.meta);
  final T value;
  final ApiResponseMeta meta;
}

final class FeatureFailure<T> extends AsyncFeatureState<T> {
  const FeatureFailure(this.failure);
  final ApiFailureDetail failure;
}

final class FeatureNotObserved<T> extends AsyncFeatureState<T> {
  const FeatureNotObserved(this.reason, this.sourceKind);
  final String reason;
  final String sourceKind;
}
