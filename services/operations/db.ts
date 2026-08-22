import { SQLDatabase } from "encore.dev/storage/sqldb";
import { createDrizzleClient } from "../shared/db/client";
import * as operationsSchema from "../shared/db/schema/operations";
import * as strategySchema from "../shared/db/schema/strategy";

export const schema = { ...operationsSchema, ...strategySchema };

export const operationsDB = new SQLDatabase("operations", {
  migrations: "./migrations",
});

export const db = createDrizzleClient(operationsDB.connectionString, schema);
