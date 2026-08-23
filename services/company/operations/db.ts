import { createDrizzleClient, DEFAULT_COMPANY_DB_URL } from "../shared/db/client";
import * as operationsSchema from "../shared/db/schema/operations";
import * as strategySchema from "../shared/db/schema/strategy";

export const schema = { ...operationsSchema, ...strategySchema };

const conn = process.env.COMPANY_DATABASE_URL || DEFAULT_COMPANY_DB_URL;
export const db = createDrizzleClient(conn, schema);
