import 'package:flutter/material.dart';

import '../../core/network/api_result.dart';
import '../state/async_feature_state.dart';

/// Task 6 — widget dùng chung cho lát dọc "truthful async state": mọi feature
/// muốn hiển thị [AsyncFeatureState] đều đi qua đây thay vì tự viết lại
/// switch-case riêng, để tránh một nơi lỡ hiển thị 503/timeout/malformed
/// giống hệt "đã tải xong, danh sách rỗng" (đúng bug mà Approvals mắc phải).
///
/// [dataBuilder] chỉ được gọi khi có [FeatureData] thật (đã tải xong thành
/// công) — nó tự quyết định hiển thị "rỗng" hay danh sách dựa trên
/// `value.isEmpty`, KHÔNG phải là nhánh riêng ở widget này.
class FeatureStateView<T> extends StatelessWidget {
  const FeatureStateView({
    super.key,
    required this.state,
    required this.onRetry,
    required this.dataBuilder,
    this.loadingBuilder,
    this.backgroundColor,
  });

  final AsyncFeatureState<T> state;
  final VoidCallback onRetry;
  final Widget Function(BuildContext context, T value, ApiResponseMeta meta) dataBuilder;
  final WidgetBuilder? loadingBuilder;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    final current = state;
    if (current is FeatureData<T>) {
      return dataBuilder(context, current.value, current.meta);
    }
    if (current is FeatureFailure<T>) {
      return _UnavailableView(failure: current.failure, onRetry: onRetry);
    }
    if (current is FeatureNotObserved<T>) {
      // Chưa từng quan sát được nguồn dữ liệu này (vd. thiếu heartbeat) —
      // vẫn là một dạng "không có gì đáng tin để hiển thị", dùng chung UI
      // "không thể tải" thay vì suy diễn thành rỗng.
      return _UnavailableView(
        failure: ApiFailureDetail(
          code: ApiFailureCode.unknown,
          message: current.reason,
        ),
        onRetry: onRetry,
      );
    }
    // FeatureInitial/FeatureLoading — chưa có kết quả nào (thành công lẫn
    // thất bại) để hiển thị, đây là trạng thái "đang tải" thuần tuý.
    return loadingBuilder?.call(context) ??
        const Center(child: CircularProgressIndicator());
  }
}

class _UnavailableView extends StatelessWidget {
  const _UnavailableView({required this.failure, required this.onRetry});

  final ApiFailureDetail failure;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off_rounded, size: 48, color: Colors.orange.shade300),
            const SizedBox(height: 14),
            const Text(
              'Không thể tải dữ liệu lúc này',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 6),
            Text(
              failure.message,
              style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            OutlinedButton(
              onPressed: onRetry,
              child: const Text('Thử lại'),
            ),
          ],
        ),
      ),
    );
  }
}
