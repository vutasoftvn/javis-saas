-- Fresh PostgreSQL bootstrap for the three canonical development data planes:
-- agent, cosa, workspace. This runs only while an empty Docker volume is initialized.
--
-- The bootstrap superuser is used only here. Each database has one migration
-- owner and one application role; applications cannot create databases, roles,
-- schemas, or tables. Supply all six passwords through the container environment.

\getenv agent_app_password AGENT_APP_PASSWORD
\getenv agent_migrator_password AGENT_MIGRATOR_PASSWORD
\getenv cosa_app_password COSA_APP_PASSWORD
\getenv cosa_migrator_password COSA_MIGRATOR_PASSWORD
\getenv workspace_app_password WORKSPACE_APP_PASSWORD
\getenv workspace_migrator_password WORKSPACE_MIGRATOR_PASSWORD

\if :{?agent_app_password}
\else
  \quit 3
\endif
\if :{?agent_migrator_password}
\else
  \quit 3
\endif
\if :{?cosa_app_password}
\else
  \quit 3
\endif
\if :{?cosa_migrator_password}
\else
  \quit 3
\endif
\if :{?workspace_app_password}
\else
  \quit 3
\endif
\if :{?workspace_migrator_password}
\else
  \quit 3
\endif

SELECT format(
  'CREATE ROLE agent_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
  :'agent_app_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agent_app')
\gexec
SELECT format(
  'CREATE ROLE agent_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
  :'agent_migrator_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agent_migrator')
\gexec
SELECT format(
  'CREATE ROLE cosa_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
  :'cosa_app_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cosa_app')
\gexec
SELECT format(
  'CREATE ROLE cosa_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
  :'cosa_migrator_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cosa_migrator')
\gexec
SELECT format(
  'CREATE ROLE workspace_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
  :'workspace_app_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'workspace_app')
\gexec
SELECT format(
  'CREATE ROLE workspace_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
  :'workspace_migrator_password'
)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'workspace_migrator')
\gexec

SELECT 'CREATE DATABASE agent OWNER agent_migrator'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agent')
\gexec
SELECT 'CREATE DATABASE cosa OWNER cosa_migrator'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cosa')
\gexec
SELECT 'CREATE DATABASE workspace OWNER workspace_migrator'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'workspace')
\gexec

REVOKE CONNECT ON DATABASE agent FROM PUBLIC;
REVOKE CONNECT ON DATABASE cosa FROM PUBLIC;
REVOKE CONNECT ON DATABASE workspace FROM PUBLIC;
GRANT CONNECT ON DATABASE agent TO agent_app, agent_migrator;
GRANT CONNECT ON DATABASE cosa TO cosa_app, cosa_migrator;
GRANT CONNECT ON DATABASE workspace TO workspace_app, workspace_migrator;

\connect agent
CREATE EXTENSION IF NOT EXISTS vector;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO agent_app;

\connect cosa
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO cosa_app;

\connect workspace
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO workspace_app;
