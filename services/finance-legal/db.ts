import { SQLDatabase } from "encore.dev/storage/sqldb";

export const financeLegalDB = new SQLDatabase("finance_legal", {
  migrations: "./migrations",
});
