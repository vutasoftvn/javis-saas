/**
 * Company MVP Response Envelopes and Helpers
 */

export type MvpDataState = "populated" | "empty";

export interface MvpSourceRef {
  readonly kind: "company_db" | "agent_db" | "object_store" | "control_plane" | "external_connector";
  readonly ref: string;
  readonly observedAt?: string;
}

export interface MvpResponseMeta {
  readonly dataState: MvpDataState;
  readonly observedAt: string;
  readonly sources: readonly MvpSourceRef[];
}

export interface MvpSuccess<T> {
  readonly data: T;
  readonly meta: MvpResponseMeta;
}

export function mvpList<T>(
  items: readonly T[],
  sources: readonly MvpSourceRef[],
  observedAt: Date = new Date()
): MvpSuccess<readonly T[]> {
  return {
    data: items,
    meta: {
      dataState: items.length > 0 ? "populated" : "empty",
      observedAt: observedAt.toISOString(),
      sources,
    },
  };
}

export function mvpItem<T>(
  item: T,
  sources: readonly MvpSourceRef[],
  observedAt: Date = new Date()
): MvpSuccess<T> {
  return {
    data: item,
    meta: {
      dataState: "populated",
      observedAt: observedAt.toISOString(),
      sources,
    },
  };
}
