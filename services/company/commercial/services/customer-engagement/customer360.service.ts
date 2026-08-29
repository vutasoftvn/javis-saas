import { APIError } from "encore.dev/api";
import { eq, and, isNull, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";

// DTOs for response serialization
interface ContactDTO {
  id: string;
  workspaceId: string;
  accountId: string | null;
  name: string;
  title: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  consentStatus: string | null;
  doNotContact: boolean;
  ownerMemberId: string | null;
  createdAt: string;
  updatedAt: string;
}

interface AccountDTO {
  id: string;
  workspaceId: string;
  name: string;
  domain: string | null;
  industry: string | null;
  sizeSegment: string | null;
  country: string | null;
  lifecycleStatus: string;
  createdAt: string;
  updatedAt: string;
}

interface SalesLeadDTO {
  id: string;
  workspaceId: string;
  accountId: string | null;
  contactId: string | null;
  name: string;
  company: string | null;
  stage: string;
  value: number | null;
  createdAt: string;
  updatedAt: string;
}

interface SalesOpportunityDTO {
  id: string;
  workspaceId: string;
  accountId: string;
  primaryContactId: string | null;
  product: string | null;
  stage: string;
  estimatedValue: number | null;
  currency: string;
  probability: number | null;
  createdAt: string;
  updatedAt: string;
}

interface CustomerDTO {
  id: string;
  workspaceId: string;
  accountId: string;
  lifecycleStatus: string;
  healthStatus: string;
  renewalDate: string | null;
  createdAt: string;
  updatedAt: string;
}

interface InvoiceDTO {
  id: string;
  workspaceId: string;
  customerId: string | null;
  invoiceNumber: string;
  amount: number;
  currency: string;
  status: string;
  dueDate: string | null;
  paidAt: string | null;
  createdAt: string;
  updatedAt: string;
}

interface SubscriptionDTO {
  id: string;
  workspaceId: string;
  customerId: string | null;
  planName: string;
  billingCycle: string;
  price: number;
  currency: string;
  status: string;
  currentPeriodStart: string | null;
  currentPeriodEnd: string | null;
  createdAt: string;
  updatedAt: string;
}

interface InteractionDTO {
  id: string;
  workspaceId: string;
  contactId: string | null;
  accountId: string | null;
  leadId: string | null;
  opportunityId: string | null;
  customerId: string | null;
  threadId: string | null;
  summary: string;
  confidence: string;
  occurredAt: string;
  createdAt: string;
}

interface Customer360DTO {
  contact: ContactDTO;
  account: AccountDTO | null;
  leads: SalesLeadDTO[];
  opportunities: SalesOpportunityDTO[];
  customer?: CustomerDTO | null;
  invoices?: InvoiceDTO[];
  subscriptions?: SubscriptionDTO[];
  recentInteractions?: InteractionDTO[];
}

interface Customer360UnverifiedDTO {
  contact: ContactDTO;
  account: AccountDTO | null;
  leads: SalesLeadDTO[];
  opportunities: SalesOpportunityDTO[];
}

function rowToContactDTO(row: typeof schema.contacts.$inferSelect): ContactDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: row.accountId ? String(row.accountId) : null,
    name: row.name,
    title: row.title || null,
    phone: row.phone || null,
    email: row.email || null,
    source: row.source || null,
    consentStatus: row.consentStatus || null,
    doNotContact: row.doNotContact,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToAccountDTO(row: typeof schema.accounts.$inferSelect): AccountDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    name: row.name,
    domain: row.domain || null,
    industry: row.industry || null,
    sizeSegment: row.sizeSegment || null,
    country: row.country || null,
    lifecycleStatus: row.lifecycleStatus,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToSalesLeadDTO(row: typeof schema.salesLeads.$inferSelect): SalesLeadDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: row.accountId ? String(row.accountId) : null,
    contactId: row.contactId ? String(row.contactId) : null,
    name: row.name,
    company: row.company || null,
    stage: row.stage,
    value: row.value || null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToSalesOpportunityDTO(row: typeof schema.salesOpportunities.$inferSelect): SalesOpportunityDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: String(row.accountId),
    primaryContactId: row.primaryContactId ? String(row.primaryContactId) : null,
    product: row.product || null,
    stage: row.stage,
    estimatedValue: row.estimatedValue || null,
    currency: row.currency,
    probability: row.probability || null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToCustomerDTO(row: typeof schema.customers.$inferSelect): CustomerDTO {
  let renewalDateStr: string | null = null;
  if (row.renewalDate) {
    if (typeof row.renewalDate === "string") {
      renewalDateStr = row.renewalDate;
    } else if (row.renewalDate && "toISOString" in row.renewalDate) {
      renewalDateStr = (row.renewalDate as Date).toISOString();
    }
  }

  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: String(row.accountId),
    lifecycleStatus: row.lifecycleStatus,
    healthStatus: row.healthStatus,
    renewalDate: renewalDateStr,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToInvoiceDTO(row: typeof schema.invoices.$inferSelect): InvoiceDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    customerId: row.customerId ? String(row.customerId) : null,
    invoiceNumber: row.invoiceNumber,
    amount: row.amount,
    currency: row.currency,
    status: row.status,
    dueDate: row.dueDate ? row.dueDate.toISOString() : null,
    paidAt: row.paidAt ? row.paidAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToSubscriptionDTO(row: typeof schema.subscriptions.$inferSelect): SubscriptionDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    customerId: row.customerId ? String(row.customerId) : null,
    planName: row.planName,
    billingCycle: row.billingCycle,
    price: row.price,
    currency: row.currency,
    status: row.status,
    currentPeriodStart: row.currentPeriodStart ? row.currentPeriodStart.toISOString() : null,
    currentPeriodEnd: row.currentPeriodEnd ? row.currentPeriodEnd.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function rowToInteractionDTO(row: typeof schema.engagementCustomerInteractions.$inferSelect): InteractionDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    contactId: row.contactId ? String(row.contactId) : null,
    accountId: row.accountId ? String(row.accountId) : null,
    leadId: row.leadId ? String(row.leadId) : null,
    opportunityId: row.opportunityId ? String(row.opportunityId) : null,
    customerId: row.customerId ? String(row.customerId) : null,
    threadId: row.threadId ? String(row.threadId) : null,
    summary: row.summary,
    confidence: row.confidence,
    occurredAt: row.occurredAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getCustomer360(
  contactId: string,
  ctx: TenantContext,
  opts?: { identityVerified?: boolean }
): Promise<Customer360DTO | Customer360UnverifiedDTO> {
  const wsId = BigInt(ctx.workspaceId);
  const cId = BigInt(contactId);

  // Load contact
  const [contact] = await db
    .select()
    .from(schema.contacts)
    .where(and(eq(schema.contacts.id, cId), eq(schema.contacts.workspaceId, wsId), isNull(schema.contacts.deletedAt)))
    .limit(1);

  if (!contact) throw APIError.notFound("contact not found");

  const contactDTO = rowToContactDTO(contact);

  // Load account
  let account: AccountDTO | null = null;
  if (contact.accountId) {
    const [accountRow] = await db
      .select()
      .from(schema.accounts)
      .where(
        and(eq(schema.accounts.id, contact.accountId), eq(schema.accounts.workspaceId, wsId), isNull(schema.accounts.deletedAt))
      )
      .limit(1);
    if (accountRow) account = rowToAccountDTO(accountRow);
  }

  // Load leads
  const leads = await db
    .select()
    .from(schema.salesLeads)
    .where(
      and(eq(schema.salesLeads.contactId, cId), eq(schema.salesLeads.workspaceId, wsId), isNull(schema.salesLeads.deletedAt))
    );
  const leadsDTO = leads.map(rowToSalesLeadDTO);

  // Load opportunities
  const opportunities = await db
    .select()
    .from(schema.salesOpportunities)
    .where(
      and(
        eq(schema.salesOpportunities.primaryContactId, cId),
        eq(schema.salesOpportunities.workspaceId, wsId),
        isNull(schema.salesOpportunities.deletedAt)
      )
    );
  const opportunitiesDTO = opportunities.map(rowToSalesOpportunityDTO);

  // Privacy gate: if identityVerified === false, return early
  if (opts?.identityVerified === false) {
    return {
      contact: contactDTO,
      account,
      leads: leadsDTO,
      opportunities: opportunitiesDTO,
    };
  }

  // Load customer (first one linked to this contact's account)
  let customer: CustomerDTO | null = null;
  if (contact.accountId) {
    const [customerRow] = await db
      .select()
      .from(schema.customers)
      .where(
        and(eq(schema.customers.accountId, contact.accountId), eq(schema.customers.workspaceId, wsId), isNull(schema.customers.deletedAt))
      )
      .limit(1);
    if (customerRow) customer = rowToCustomerDTO(customerRow);
  }

  // Load invoices
  let invoices: InvoiceDTO[] = [];
  if (customer) {
    const invoiceRows = await db
      .select()
      .from(schema.invoices)
      .where(
        and(eq(schema.invoices.customerId, BigInt(customer.id)), eq(schema.invoices.workspaceId, wsId), isNull(schema.invoices.deletedAt))
      );
    invoices = invoiceRows.map(rowToInvoiceDTO);
  }

  // Load subscriptions
  let subscriptions: SubscriptionDTO[] = [];
  if (customer) {
    const subscriptionRows = await db
      .select()
      .from(schema.subscriptions)
      .where(
        and(eq(schema.subscriptions.customerId, BigInt(customer.id)), eq(schema.subscriptions.workspaceId, wsId), isNull(schema.subscriptions.deletedAt))
      );
    subscriptions = subscriptionRows.map(rowToSubscriptionDTO);
  }

  // Load recent interactions (limit 20, order by occurredAt desc)
  const interactions = await db
    .select()
    .from(schema.engagementCustomerInteractions)
    .where(and(eq(schema.engagementCustomerInteractions.contactId, cId), eq(schema.engagementCustomerInteractions.workspaceId, wsId)))
    .orderBy(desc(schema.engagementCustomerInteractions.occurredAt))
    .limit(20);
  const recentInteractions = interactions.map(rowToInteractionDTO);

  return {
    contact: contactDTO,
    account,
    leads: leadsDTO,
    opportunities: opportunitiesDTO,
    customer,
    invoices,
    subscriptions,
    recentInteractions,
  };
}
