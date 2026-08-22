import { SQLDatabase } from "encore.dev/storage/sqldb";
import { createDrizzleClient } from "../shared/db/client";
import * as schema from "../shared/db/schema/finance-legal";

export const financeLegalDB = new SQLDatabase("finance_legal", {
  migrations: "./migrations",
});

export const db = createDrizzleClient(financeLegalDB.connectionString, schema);
export { schema };
