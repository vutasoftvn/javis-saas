#!/usr/bin/env node
// Wrapper mỏng cho `make test-db-reset`.
//
// Toàn bộ logic an toàn + phá huỷ nằm ở scripts/test-db-reset-lib.mjs. Lệnh này
// CHỈ dành cho môi trường test: nó tái tạo đúng ba database test disposable từ
// migration baseline 001 Startup Core. Nó KHÔNG có mặt trong deploy,
// migrate-all, dev-migrate hay dev-stack.
//
// Yêu cầu: APP_ENV=test và TEST_DATABASE_RESET=CONFIRM_COSA_STARTUP_CORE_RESET,
// cùng ba biến *_TEST_MIGRATOR_DATABASE_URL trỏ đúng javis_agent_test,
// javis_cosa_test và javis_workspace_test.
import { runTestDatabaseReset } from "./test-db-reset-lib.mjs";

runTestDatabaseReset(process.env)
  .then((planes) => {
    // eslint-disable-next-line no-console
    console.log(`[test-db-reset] completed planes: ${planes.join(" -> ")}`);
  })
  .catch((err) => {
    // eslint-disable-next-line no-console
    console.error(err.message);
    process.exit(1);
  });
