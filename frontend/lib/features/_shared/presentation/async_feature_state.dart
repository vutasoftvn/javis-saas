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
