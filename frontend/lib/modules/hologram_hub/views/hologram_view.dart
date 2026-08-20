import 'package:flutter/material.dart';

class HologramView extends StatelessWidget {
  final String runId;

  const HologramView({Key? key, required this.runId}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hologram Run Inspector')),
      body: const Center(
        child: Text('Timeline sự kiện và thẻ trạng thái an toàn (không có secret).'),
      ),
    );
  }
}
