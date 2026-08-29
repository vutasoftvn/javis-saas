import { api, Header, Query } from "encore.dev/api";
import {
  listRegulationSources,
  listObligationTemplates,
  createRegulationVersion,
  RegulationSourceView,
  ObligationTemplateView,
} from "../services/regulation-catalog.service";

export interface ListRegulationSourcesParams {
  layer?: Query<string>;
  activeOnly?: Query<boolean>;
}

export interface ListRegulationSourcesResponse {
  sources: RegulationSourceView[];
}

export interface ListObligationTemplatesParams {
  regulationVersionId?: Query<string>;
}

export interface ListObligationTemplatesResponse {
  templates: ObligationTemplateView[];
}

export interface CreateRegulationVersionParams {
  authorization?: Header<"Authorization">;
  regulationSourceId: string;
  version: string;
  effectiveFrom: string;
  effectiveTo?: string;
  supersededById?: string;
}

export const getRegulationSources = api(
  { method: "GET", path: "/finance-legal/regulation-sources", expose: true },
  async (params: ListRegulationSourcesParams): Promise<ListRegulationSourcesResponse> => {
    const sources = await listRegulationSources({
      layer: params.layer,
      activeOnly: params.activeOnly,
    });
    return { sources };
  }
);

export const getObligationTemplates = api(
  { method: "GET", path: "/finance-legal/obligation-templates", expose: true },
  async (params: ListObligationTemplatesParams): Promise<ListObligationTemplatesResponse> => {
    const templates = await listObligationTemplates(params.regulationVersionId);
    return { templates };
  }
);

export const postRegulationVersion = api(
  { method: "POST", path: "/finance-legal/regulation-versions", expose: true },
  async (params: CreateRegulationVersionParams): Promise<{ id: string }> => {
    return createRegulationVersion({
      regulationSourceId: BigInt(params.regulationSourceId),
      version: params.version,
      effectiveFrom: params.effectiveFrom,
      effectiveTo: params.effectiveTo,
      supersededById: params.supersededById ? BigInt(params.supersededById) : undefined,
    });
  }
);
