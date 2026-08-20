import 'package:flutter/material.dart';

class ArtifactViewerWidget extends StatelessWidget {
  final Map<String, dynamic> payload;

  const ArtifactViewerWidget({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Sản phẩm đầu ra (Artifact)';
    final summary = payload['summary'] ?? payload['file_path'] ?? '';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0x2000F0FF),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x4000F0FF)),
      ),
      child: Row(
        children: [
          const Icon(Icons.description_outlined, color: Color(0xFF00F0FF), size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 11)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
