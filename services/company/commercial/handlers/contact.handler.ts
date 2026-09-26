import { api, Header, Query } from "encore.dev/api";
import {
  Contact,
  CreateContactParams as BaseCreateContactParams,
  createContactService,
  getContactService,
  listContactsService,
} from "../services/contact.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { Contact };

export interface CreateContactParams extends BaseCreateContactParams {
  authorization?: Header<"Authorization">;
}

export const createContact = api(
  { method: "POST", path: "/commercial/contacts", expose: true },
  async (params: CreateContactParams): Promise<Contact> => {
    return createContactService(params, params.authorization);
  }
);

export const getContact = api(
  { method: "GET", path: "/commercial/contacts/:id", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Contact> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getContactService(id, ctx);
  }
);

// Dashboard CRM — danh sách contact, lọc tuỳ chọn theo account.
export const listContacts = api(
  { method: "GET", path: "/commercial/workspaces/:workspaceId/contacts", expose: true },
  async (params: {
    workspaceId: string;
    accountId?: Query<string>;
    authorization?: Header<"Authorization">;
  }): Promise<{ contacts: Contact[] }> => {
    const contacts = await listContactsService(params.workspaceId, params.authorization, {
      accountId: params.accountId,
    });
    return { contacts };
  }
);
