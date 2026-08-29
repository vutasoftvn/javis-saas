import { createDrizzleClient, DEFAULT_COMPANY_DB_URL } from "../shared/db/client";
import * as financeLegalSchema from "../shared/db/schema/finance-legal";
import * as legalSchema from "../shared/db/schema/legal";

const schema = { ...financeLegalSchema, ...legalSchema };
const conn = process.env.COMPANY_DATABASE_URL || DEFAULT_COMPANY_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };

