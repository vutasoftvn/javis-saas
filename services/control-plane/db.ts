import { SQLDatabase } from "encore.dev/storage/sqldb";

export const controlPlaneDB = new SQLDatabase("control_plane", {
  migrations: "./migrations",
});
