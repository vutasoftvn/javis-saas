import { SQLDatabase } from "encore.dev/storage/sqldb";
import { createDrizzleClient } from "../shared/db/client";
import * as schema from "../shared/db/schema/commercial";

export const commercialDB = new SQLDatabase("commercial", {
  migrations: "./migrations",
});

export const db = createDrizzleClient(commercialDB.connectionString, schema);
export { schema };
