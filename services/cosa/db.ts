import { createDrizzleClient, DEFAULT_COSA_DB_URL } from "./storage/client";
import * as schema from "./storage/schema";

const conn = process.env.COSA_DATABASE_URL || DEFAULT_COSA_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };
