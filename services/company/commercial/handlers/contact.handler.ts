import { api, Header } from "encore.dev/api";
import { Contact, CreateContactParams as BaseCreateContactParams, createContactService, getContactService } from "../services/contact.service";

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
  async ({ id, authorization }: { id: string; authorization?: Header<"Authorization"> }): Promise<Contact> => {
    return getContactService(id, authorization);
  }
);
