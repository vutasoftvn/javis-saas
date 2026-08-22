import { SQLDatabase } from "encore.dev/storage/sqldb";

export const commercialDB = new SQLDatabase("commercial", {
  migrations: "./migrations",
});
