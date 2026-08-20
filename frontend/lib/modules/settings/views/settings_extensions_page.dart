import 'package:flutter/material.dart';
import '../services/extensions_service.dart';

class SettingsExtensionsPage extends StatefulWidget {
  const SettingsExtensionsPage({Key? key}) : super(key: key);

  @override
  State<SettingsExtensionsPage> createState() => _SettingsExtensionsPageState();
}

class _SettingsExtensionsPageState extends State<SettingsExtensionsPage> {
  late ExtensionsService _extensionsService;
  List<dynamic> _extensions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _extensionsService = ExtensionsService(
      baseUrl: 'http://localhost:8000',
      workspaceId: '1', // Hardcoded for MVP
    );
    _loadExtensions();
  }

  Future<void> _loadExtensions() async {
    setState(() => _isLoading = true);
    try {
      final extensions = await _extensionsService.getExtensions();
      setState(() {
        _extensions = extensions;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _toggleStatus(String extensionId, String currentStatus) async {
    final newStatus = currentStatus == 'enabled' ? 'disabled' : 'enabled';
    try {
      await _extensionsService.updateExtensionStatus(extensionId, newStatus);
      await _loadExtensions();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Extensions Settings')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _extensions.length,
              itemBuilder: (context, index) {
                final ext = _extensions[index];
                final isEnabled = ext['status'] == 'enabled' || ext['status'] == 'installed';
                
                return Card(
                  margin: const EdgeInsets.all(8),
                  child: ListTile(
                    title: Text(ext['extension_id']),
                    subtitle: Text('Status: ${ext['status']}\nCapabilities: ${ext['capabilities'].length}'),
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
