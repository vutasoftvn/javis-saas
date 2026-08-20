import 'package:flutter/material.dart';

class ProviderCard extends StatelessWidget {
  final String providerName;
  final String mode; // e.g., cosa_governed, isolated_coding
  final String status;

  const ProviderCard({
    Key? key,
    required this.providerName,
    required this.mode,
    required this.status,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.memory),
        title: Text('Provider: $providerName'),
        subtitle: Text('Mode: $mode | Status: $status'),
        trailing: mode == 'isolated_coding' 
            ? const Icon(Icons.shield, color: Colors.green)
            : const Icon(Icons.security, color: Colors.blue),
      ),
    );
  }
}
