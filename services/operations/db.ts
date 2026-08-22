import { SQLDatabase } from "encore.dev/storage/sqldb";

export const operationsDB = new SQLDatabase("operations", {
  migrations: "./migrations",
});
