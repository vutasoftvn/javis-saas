# COSA Contributor Cookbook

This cookbook provides canonical recipes for extending the COSA ecosystem without violating its architectural invariants or governance boundaries.

## Recipes

1. [How to add a Native Tool](./ADD_NATIVE_TOOL.md)
2. How to add a Skill (coming soon)
3. How to add a Workflow Node & UI Renderer (coming soon)
4. How to add an MCP Connector (coming soon)
5. How to add an Executor Provider (coming soon)
6. How to add an Event Projection (coming soon)

## Core Principles

- **No Shared State**: Extensions operate strictly on inputs and return outputs.
- **Governed Execution**: Extensions cannot execute bypassing the `ExecutionScope`.
- **Immutable Events**: Extensions must emit state changes as immutable events via the `WorkflowRunner`.
