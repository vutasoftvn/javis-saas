import { SQLDatabase } from "encore.dev/storage/sqldb";

export const tasksDB = new SQLDatabase("tasks", {
  migrations: "./migrations",
});
