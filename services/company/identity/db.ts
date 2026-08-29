import { createDrizzleClient, DEFAULT_COMPANY_DB_URL } from "../shared/db/client";
import * as identitySchema from "../shared/db/schema/identity";
import * as legalSchema from "../shared/db/schema/legal";

const schema = { ...identitySchema, ...legalSchema };
const conn = process.env.COMPANY_DATABASE_URL || DEFAULT_COMPANY_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };

