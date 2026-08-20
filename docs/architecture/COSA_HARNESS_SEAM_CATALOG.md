# COSA Harness Seam Catalog

This document defines the architectural seams within the COSA Harness. A seam is a formal interface (Protocol) that decouples the core business logic from specific provider implementations (e.g. LLM providers, Tool engines, Connectors).

## Seams

1. **model**: `ModelProvider`
2. **tool**: `ToolBackend`
3. **connector**: `ConnectorProvider`
4. **executor**: `ExecutorProvider`
5. **sandbox**: `SandboxProvider`
6. **knowledge**: `KnowledgeProvider`
7. **event_store**: `EventStore`
8. **runtime**: `RuntimeAdapter`

Each seam enforces strict contract tests found in `backend/app/workforce/extensions/contracts.py`.
