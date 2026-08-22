import { SQLDatabase } from "encore.dev/storage/sqldb";

export const okrDB = new SQLDatabase("okr", {
  migrations: "./migrations",
});
