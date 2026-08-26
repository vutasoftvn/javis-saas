import 'package:flutter/material.dart';
import '../../../core/manifest/test_capability_manifest.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/secure_storage_service.dart';
import '../services/extensions_service.dart';

class SettingsExtensionsPage extends StatefulWidget {
  const SettingsExtensionsPage({super.key});

  @override
  State<SettingsExtensionsPage> createState() => _SettingsExtensionsPageState();
}

class _SettingsExtensionsPageState extends State<SettingsExtensionsPage> {
  ExtensionsService? _extensionsService;
  List<dynamic> _extensions = [];
  bool _isLoading = true;
  bool _isSupported = false;

  @override
  void initState() {
    super.initState();
    _initServiceAndLoad();
  }

  Future<void> _initServiceAndLoad() async {
    _isSupported = TestCapabilityManifest.current.legacyExtensionsSupported;
    if (!_isSupported) {
      setState(() => _isLoading = false);
      return;
    }

    final workspaceId = await SecureStorageService.read('workspace_id') ?? '';
    _extensionsService = ExtensionsService(
      baseUrl: ApiClient.agentOsBaseUrl,
      workspaceId: workspaceId,
    );
    await _loadExtensions();
  }

  Future<void> _loadExtensions() async {
    if (_extensionsService == null) return;
    setState(() => _isLoading = true);
    try {
      final extensions = await _extensionsService!.getExtensions();
      if (!mounted) return;
      setState(() {
        _extensions = extensions;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _toggleStatus(String extensionId, String currentStatus) async {
    if (_extensionsService == null) return;
    final newStatus = currentStatus == 'enabled' ? 'disabled' : 'enabled';
    try {
      await _extensionsService!.updateExtensionStatus(extensionId, newStatus);
      await _loadExtensions();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Extensions Settings')),
      body: !_isSupported
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Card(
                  elevation: 2,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.extension_off_outlined, size: 48, color: Theme.of(context).colorScheme.outline),
                        const SizedBox(height: 16),
                        Text(
                          'Tiện ích mở rộng (Extensions)',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Tính năng tiện ích mở rộng đang được chuyển đổi sang nền tảng AgentOS & Control Plane chuẩn hóa. Các công cụ và kỹ năng hiện được điều phối trực tiếp qua COSA Capabilities.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            )
          : _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _extensions.isEmpty
                  ? Center(
                      child: Text(
                        'Chưa có tiện ích mở rộng nào được cài đặt',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    )
                  : ListView.builder(
                      itemCount: _extensions.length,
                      itemBuilder: (context, index) {
                        final ext = _extensions[index];
                        final isEnabled = ext['status'] == 'enabled' || ext['status'] == 'installed';

                        return Card(
                          margin: const EdgeInsets.all(8),
                          child: ListTile(
                            title: Text(ext['extension_id'] ?? 'Unknown'),
                            subtitle: Text('Status: ${ext['status']}\nCapabilities: ${(ext['capabilities'] as List?)?.length ?? 0}'),
                            trailing: Switch(
                              value: isEnabled,
                              onChanged: (val) => _toggleStatus(ext['extension_id'], ext['status']),
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
