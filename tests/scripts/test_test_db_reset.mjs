import test from "node:test";
import assert from "node:assert/strict";
import {
  assertResetPreconditions,
  parseResetTargets,
} from "../../scripts/test-db-reset-lib.mjs";

const safeEnv = {
  APP_ENV: "test",
  TEST_DATABASE_RESET: "CONFIRM_COSA_STARTUP_CORE_RESET",
  AGENT_TEST_MIGRATOR_DATABASE_URL:
    "postgresql://agent_migrator:x@127.0.0.1/javis_agent_test",
  COSA_TEST_MIGRATOR_DATABASE_URL:
    "postgresql://cosa_migrator:x@127.0.0.1/javis_cosa_test",
  WORKSPACE_TEST_MIGRATOR_DATABASE_URL:
    "postgresql://workspace_migrator:x@127.0.0.1/javis_workspace_test",
};

test("accepts only three exact test database names", () => {
  assert.doesNotThrow(() =>
    assertResetPreconditions(safeEnv, parseResetTargets(safeEnv))
  );
  assert.throws(
    () =>
      assertResetPreconditions(
        { ...safeEnv, APP_ENV: "development" },
        parseResetTargets(safeEnv)
      ),
    /APP_ENV=test/
  );
});

test("rejects an absent or wrong confirmation phrase", () => {
  assert.throws(
    () => {
      const env = { ...safeEnv };
      delete env.TEST_DATABASE_RESET;
      assertResetPreconditions(env, parseResetTargets(env));
    },
    /CONFIRM_COSA_STARTUP_CORE_RESET/
  );
  assert.throws(
    () =>
      assertResetPreconditions(
        { ...safeEnv, TEST_DATABASE_RESET: "CONFIRM_COSA_STARTUP_CORE_RESET " },
        parseResetTargets(safeEnv)
      ),
    /CONFIRM_COSA_STARTUP_CORE_RESET/
  );
  assert.throws(
    () =>
      assertResetPreconditions(
        { ...safeEnv, TEST_DATABASE_RESET: "CONFIRM_FOUNDER_TRIAL_MVP_RESET" },
        parseResetTargets(safeEnv)
      ),
    /CONFIRM_COSA_STARTUP_CORE_RESET/
  );
});

test("rejects a target URL that points at the wrong database name", () => {
  const env = {
    ...safeEnv,
    // Agent slot points at a database whose name ends in `cosa`, not the
    // expected `javis_agent_test`.
    AGENT_TEST_MIGRATOR_DATABASE_URL:
      "postgresql://agent_migrator:x@127.0.0.1/javis_cosa_test",
  };
  assert.throws(
    () => assertResetPreconditions(env, parseResetTargets(env)),
    /javis_agent_test/
  );
});

test("rejects two slots that resolve to the same database", () => {
  // COSA slot pointed at the agent database: rejected before any DDL, whether
  // by the exact-name guard or the distinct-tuple guard.
  const env = {
    ...safeEnv,
    COSA_TEST_MIGRATOR_DATABASE_URL:
      "postgresql://cosa_migrator:x@127.0.0.1:5432/javis_agent_test",
  };
  assert.throws(
    () => assertResetPreconditions(env, parseResetTargets(env)),
    /javis_cosa_test|distinct|duplicate|same/i
  );
});

test("rejects a test URL equal to a non-test migrator URL", () => {
  const env = {
    ...safeEnv,
    COSA_MIGRATOR_DATABASE_URL:
      "postgresql://cosa_migrator:x@127.0.0.1/javis_cosa_test",
  };
  assert.throws(
    () => assertResetPreconditions(env, parseResetTargets(env)),
    /non-test|COSA_MIGRATOR_DATABASE_URL/i
  );
});

test("rejects a missing test migrator URL", () => {
  const env = { ...safeEnv };
  delete env.WORKSPACE_TEST_MIGRATOR_DATABASE_URL;
  assert.throws(
    () => parseResetTargets(env),
    /WORKSPACE_TEST_MIGRATOR_DATABASE_URL/
  );
});
