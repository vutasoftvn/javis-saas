import 'package:flutter/material.dart';

class FeatureNotEnabledView extends StatelessWidget {
  const FeatureNotEnabledView({super.key, required this.featureName});

  final String featureName;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.lock_outline, size: 48),
            const SizedBox(height: 16),
            Text('$featureName chưa được bật', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            const Text('Quản trị viên workspace có thể bật tính năng này trong cài đặt.'),
          ],
        ),
      ),
    );
  }
}
