import { createDrizzleClient, DEFAULT_COMPANY_DB_URL } from "../shared/db/client";
import * as commercialSchema from "../shared/db/schema/commercial";
import * as engagementSchema from "../shared/db/schema/customer-engagement";

const schema = { ...commercialSchema, ...engagementSchema };
const conn = process.env.COMPANY_DATABASE_URL || DEFAULT_COMPANY_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };
