import { SQLDatabase } from "encore.dev/storage/sqldb";
import { createDrizzleClient } from "../shared/db/client";
import * as schema from "../shared/db/schema/control-plane";

export const controlPlaneDB = new SQLDatabase("control_plane", {
  migrations: "./migrations",
});

export const db = createDrizzleClient(controlPlaneDB.connectionString, schema);
export { schema };
