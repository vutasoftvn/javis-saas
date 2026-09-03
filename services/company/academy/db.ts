import { createDrizzleClient, DEFAULT_WORKSPACE_DB_URL } from "../shared/db/client";
import * as academySchema from "../shared/db/schema/academy";

const schema = { ...academySchema };
const conn = process.env.WORKSPACE_DATABASE_URL || DEFAULT_WORKSPACE_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };
