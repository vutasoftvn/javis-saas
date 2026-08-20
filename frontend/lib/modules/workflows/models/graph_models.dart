class GraphNode {
  final String id;
  final String type;
  final String definitionId;
  final Map<String, dynamic> config;
  // Offset cho toạ độ x, y trên canvas (UI specific)
  double x;
  double y;

  GraphNode({
    required this.id,
    required this.type,
    required this.definitionId,
    this.config = const {},
    this.x = 0,
    this.y = 0,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type,
        'definition_id': definitionId,
        'config': config,
        'x': x,
        'y': y,
      };
}

class GraphEdge {
  final String id;
  final String sourceNodeId;
  final String sourcePort;
  final String targetNodeId;
  final String targetPort;

  GraphEdge({
    required this.id,
    required this.sourceNodeId,
    required this.sourcePort,
    required this.targetNodeId,
    required this.targetPort,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'source_node_id': sourceNodeId,
        'source_port': sourcePort,
        'target_node_id': targetNodeId,
        'target_port': targetPort,
      };
}

class WorkflowGraph {
  final String version;
  String entryNodeId;
  final Map<String, GraphNode> nodes;
  final List<GraphEdge> edges;

  WorkflowGraph({
    this.version = '1.0',
    required this.entryNodeId,
    required this.nodes,
    required this.edges,
  });

  Map<String, dynamic> toJson() => {
        'version': version,
        'entry_node_id': entryNodeId,
        'nodes': nodes.map((k, v) => MapEntry(k, v.toJson())),
        'edges': edges.map((e) => e.toJson()).toList(),
      };
}
