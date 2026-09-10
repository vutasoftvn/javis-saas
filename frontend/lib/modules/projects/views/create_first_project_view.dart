import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/routing/app_routes.dart';
import '../../strategy/services/strategy_service.dart';

/// Màn tạo project đầu tiên khi workspace chưa có project nào.
/// Thay cho luồng kickoff/stage-gate framework cũ — chỉ nhận title + mô tả;
/// lifecycle stage khởi tạo mặc định `P0_DISCOVERY` ở backend và được chuyển
/// thủ công qua màn Project Operating Loop.
class CreateFirstProjectView extends StatefulWidget {
  const CreateFirstProjectView({super.key});

  @override
  State<CreateFirstProjectView> createState() => _CreateFirstProjectViewState();
}

class _CreateFirstProjectViewState extends State<CreateFirstProjectView> {
  final _title = TextEditingController();
  final _description = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty) {
      setState(() => _error = 'Vui lòng nhập tên project');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await StrategyService().createBasicProject(
        title: _title.text.trim(),
        description: _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
      );
      Get.offAllNamed(AppRoutes.hub);
    } catch (e) {
      setState(() {
        _submitting = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEn = Get.locale?.languageCode == 'en';
    return Scaffold(
      appBar: AppBar(
        title: Text(isEn ? 'Create your first project' : 'Tạo project đầu tiên'),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _title,
                  decoration: InputDecoration(
                    labelText: isEn ? 'Project name' : 'Tên project',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _description,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: isEn ? 'Description (optional)' : 'Mô tả (tuỳ chọn)',
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: Colors.red)),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: _submitting
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text(isEn ? 'Create project' : 'Tạo project'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
