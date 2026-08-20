import 'package:flutter/material.dart';
import '../models/graph_models.dart';

class NodeInspector extends StatelessWidget {
  final GraphNode? selectedNode;
  
  const NodeInspector({Key? key, this.selectedNode}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (selectedNode == null) {
      return const Center(child: Text('Chưa chọn node nào'));
    }

    return Container(
      padding: const EdgeInsets.all(16),
      width: 300,
      color: Colors.white,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Node Inspector', style: Theme.of(context).textTheme.titleLarge),
          const Divider(),
          Text('ID: ${selectedNode!.id}'),
          Text('Type: ${selectedNode!.type}'),
          Text('Definition: ${selectedNode!.definitionId}'),
          const SizedBox(height: 16),
          const Text('Configuration:', style: TextStyle(fontWeight: FontWeight.bold)),
          ...selectedNode!.config.entries.map((e) => 
            Text('${e.key}: ${e.value}')
          ),
          const Spacer(),
          // Placeholder cho validation messages, risk summary
          Container(
            padding: const EdgeInsets.all(8),
            color: Colors.amber.shade50,
            child: const Row(
              children: [
                Icon(Icons.warning, color: Colors.amber),
                SizedBox(width: 8),
                Expanded(child: Text('Node này an toàn. (Mock diagnostic)')),
              ],
            ),
          )
        ],
      ),
    );
  }
}
