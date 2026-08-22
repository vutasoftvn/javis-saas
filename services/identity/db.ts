import { SQLDatabase } from "encore.dev/storage/sqldb";
import { createDrizzleClient } from "../shared/db/client";
import * as schema from "../shared/db/schema/identity";

export const identityDB = new SQLDatabase("identity", {
  migrations: "./migrations",
});

export const db = createDrizzleClient(identityDB.connectionString, schema);
export { schema };
