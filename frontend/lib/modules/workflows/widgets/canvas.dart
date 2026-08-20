import 'package:flutter/material.dart';
import '../models/graph_models.dart';

class WorkflowCanvas extends StatefulWidget {
  final WorkflowGraph graph;
  final Function(GraphNode) onNodeSelected;

  const WorkflowCanvas({
    Key? key,
    required this.graph,
    required this.onNodeSelected,
  }) : super(key: key);

  @override
  State<WorkflowCanvas> createState() => _WorkflowCanvasState();
}

class _WorkflowCanvasState extends State<WorkflowCanvas> {
  @override
  Widget build(BuildContext context) {
    return InteractiveViewer(
      constrained: false,
      boundaryMargin: const EdgeInsets.all(2000),
      minScale: 0.1,
      maxScale: 2.0,
      child: Container(
        width: 4000,
        height: 4000,
        color: Colors.grey[100], // Nền canvas
        child: Stack(
          children: [
            // Vẽ lines (edges)
            CustomPaint(
              size: const Size(4000, 4000),
              painter: _EdgePainter(widget.graph.edges, widget.graph.nodes),
            ),
            // Vẽ nodes
            ...widget.graph.nodes.values.map((node) {
              return Positioned(
                left: node.x,
                top: node.y,
                child: GestureDetector(
                  onTap: () => widget.onNodeSelected(node),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border.all(color: Colors.blue),
                      borderRadius: BorderRadius.circular(8),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black12,
                          blurRadius: 4,
                        ),
                      ],
                    ),
                    child: Text(node.definitionId),
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _EdgePainter extends CustomPainter {
  final List<GraphEdge> edges;
  final Map<String, GraphNode> nodes;

  _EdgePainter(this.edges, this.nodes);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.grey
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    for (final edge in edges) {
      final source = nodes[edge.sourceNodeId];
      final target = nodes[edge.targetNodeId];
      
      if (source != null && target != null) {
        // Tạm thời vẽ đường thẳng nối 2 góc trên cùng của node
        canvas.drawLine(
          Offset(source.x, source.y),
          Offset(target.x, target.y),
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
