import { Topic } from "encore.dev/pubsub";
import { DomainEvent, makeDomainEvent, OKR_PROGRESS_UPDATED } from "../shared/events";

export interface OkrProgressUpdatedPayload {
  objectiveId: number;
  score: number;
}

export type OkrProgressUpdatedEvent = DomainEvent<typeof OKR_PROGRESS_UPDATED, OkrProgressUpdatedPayload>;

export const okrEvents = new Topic<OkrProgressUpdatedEvent>("okr-events", {
  deliveryGuarantee: "at-least-once",
});

export function buildOkrProgressUpdatedEvent(objectiveId: number, score: number): OkrProgressUpdatedEvent {
  return makeDomainEvent(OKR_PROGRESS_UPDATED, { objectiveId, score });
}
