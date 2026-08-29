import { createDrizzleClient, DEFAULT_WORKSPACE_DB_URL } from "../shared/db/client";
import * as operationsSchema from "../shared/db/schema/operations";
import * as strategySchema from "../shared/db/schema/strategy";
import * as integrationSchema from "../shared/db/schema/integration";
import * as financeLegalSchema from "../shared/db/schema/finance-legal";
import * as legalSchema from "../shared/db/schema/legal";

export const schema = {
  ...operationsSchema,
  ...strategySchema,
  ...integrationSchema,
  ...financeLegalSchema,
  ...legalSchema,
};

const conn = process.env.WORKSPACE_DATABASE_URL || DEFAULT_WORKSPACE_DB_URL;
export const db = createDrizzleClient(conn, schema);
