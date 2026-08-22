import 'package:flutter/material.dart';

class ProfileCompositionView extends StatelessWidget {
  const ProfileCompositionView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile Composition')),
      body: const Center(
        child: Text('Danh sách profile và giải thích các tool không khả dụng sẽ hiển thị ở đây.'),
      ),
    );
  }
}
