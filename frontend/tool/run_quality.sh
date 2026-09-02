#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
flutter analyze
flutter test test/core/services/secure_storage_service_test.dart -r compact
flutter test test/modules/workspace_picker/workspace_picker_controller_test.dart -r compact
flutter test -r compact
cd ..
node scripts/check_frontend_api_contracts.mjs
