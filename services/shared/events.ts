// Canonical event names follow "entity.action" — mirrors
// backend/agentos/core/events.py EVENT_* constants on the Python side.
// See docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md §3.9/§46.
export const TASK_CREATED = "task.created";
export const TASK_COMPLETED = "task.completed";
export const OKR_PROGRESS_UPDATED = "okr.progress_updated";

export interface DomainEvent<Name extends string, Payload> {
  name: Name;
  emittedAt: string;
  payload: Payload;
}

export function makeDomainEvent<Name extends string, Payload>(
  name: Name,
  payload: Payload
): DomainEvent<Name, Payload> {
  return { name, emittedAt: new Date().toISOString(), payload };
}
