import 'package:flutter/material.dart';
import 'package:frontend/core/services/workspace_service.dart';
import 'package:frontend/data/models/workspace_file_model.dart';

class CompanyWorkspaceView extends StatefulWidget {
  const CompanyWorkspaceView({super.key});

  @override
  State<CompanyWorkspaceView> createState() => _CompanyWorkspaceViewState();
}

class _CompanyWorkspaceViewState extends State<CompanyWorkspaceView> {
  List<WorkspaceFileModel> _files = [];
  WorkspaceFileModel? _selectedFile;
  final TextEditingController _contentController = TextEditingController();
  bool _isLoading = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadFiles();
  }

  Future<void> _loadFiles() async {
    setState(() => _isLoading = true);
    final files = await WorkspaceService.listFiles();
    setState(() {
      _files = files;
      _isLoading = false;
      if (files.isNotEmpty && _selectedFile == null) {
        _selectFile(files.first);
      }
    });
  }

  Future<void> _selectFile(WorkspaceFileModel file) async {
    setState(() {
      _selectedFile = file;
      _isLoading = true;
    });
    final content = await WorkspaceService.readFile(file.relativePath);
    setState(() {
      _contentController.text = content ?? '';
      _isLoading = false;
    });
  }

  Future<void> _saveCurrentFile() async {
    if (_selectedFile == null) return;
    setState(() => _isSaving = true);
    final ok = await WorkspaceService.writeFile(
      _selectedFile!.relativePath,
      _contentController.text,
    );
    setState(() => _isSaving = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? 'Saved successfully' : 'Failed to save file'),
          backgroundColor: ok ? const Color(0xFF10B981) : Colors.redAccent,
        ),
      );
    }
  }

  Future<void> _resetCurrentFileToDefault() async {
    if (_selectedFile == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Reset to Default?', style: TextStyle(color: Colors.white)),
        content: Text(
          'Are you sure you want to reset ${_selectedFile!.relativePath} to system default?',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.amber[700]),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Reset to Default'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final defaultContent = await WorkspaceService.resetToDefault(
        _selectedFile!.relativePath,
      );
      if (defaultContent != null) {
        setState(() => _contentController.text = defaultContent);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Reset to system default completed.'),
              backgroundColor: Color(0xFF10B981),
            ),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: const Row(
          children: [
            Icon(Icons.folder_special_rounded, color: Color(0xFF38BDF8), size: 20),
            SizedBox(width: 8),
            Text('Company Workspace (~/.cosa/)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          if (_selectedFile != null) ...[
            TextButton.icon(
              icon: const Icon(Icons.restart_alt_rounded, size: 16, color: Colors.amberAccent),
              label: const Text('Reset to Default', style: TextStyle(color: Colors.amberAccent, fontSize: 13)),
              onPressed: _resetCurrentFileToDefault,
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF38BDF8),
                foregroundColor: Colors.black,
              ),
              icon: _isSaving
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                  : const Icon(Icons.save_rounded, size: 16),
              label: const Text('Save Changes', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
              onPressed: _isSaving ? null : _saveCurrentFile,
            ),
            const SizedBox(width: 12),
          ],
        ],
      ),
      body: Row(
        children: [
          // Sidebar Tree
          Container(
            width: 280,
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B).withValues(alpha: 0.5),
              border: Border(right: BorderSide(color: Colors.white.withValues(alpha: 0.08))),
            ),
            child: _isLoading && _files.isEmpty
                ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                : ListView.builder(
                    itemCount: _files.length,
                    itemBuilder: (ctx, idx) {
                      final f = _files[idx];
                      final isSelected = _selectedFile?.relativePath == f.relativePath;
                      return ListTile(
                        dense: true,
                        selected: isSelected,
                        selectedTileColor: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                        leading: Icon(
                          f.isProtected ? Icons.lock_outline_rounded : Icons.description_outlined,
                          size: 16,
                          color: isSelected ? const Color(0xFF38BDF8) : Colors.white60,
                        ),
                        title: Text(
                          f.relativePath,
                          style: TextStyle(
                            color: isSelected ? Colors.white : Colors.white70,
                            fontSize: 12,
                            fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                        onTap: () => _selectFile(f),
                      );
                    },
                  ),
          ),

          // Editor View
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                : Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: TextField(
                      controller: _contentController,
                      maxLines: null,
                      expands: true,
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'monospace',
                        fontSize: 13,
                        height: 1.5,
                      ),
                      decoration: const InputDecoration(
                        border: InputBorder.none,
                        hintText: 'Markdown content...',
                        hintStyle: TextStyle(color: Colors.white30),
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
