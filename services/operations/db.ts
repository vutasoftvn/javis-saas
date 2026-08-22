import { SQLDatabase } from "encore.dev/storage/sqldb";
import { createDrizzleClient } from "../shared/db/client";
import * as schema from "../shared/db/schema/operations";

export const operationsDB = new SQLDatabase("operations", {
  migrations: "./migrations",
});

export const db = createDrizzleClient(operationsDB.connectionString, schema);
export { schema };
