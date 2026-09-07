-- Migration 032: Fast-follow correction to Task 1's contract
-- (models.model_provider_profiles, migration 030) — thêm cột base_url TEXT
-- nullable. LOCAL_OPENAI_COMPATIBLE (provider "local-first" chính của cả
-- plan 2026-09-07-local-first-model-routing) không thể reach được endpoint
-- tự host nếu thiếu base_url — đây là defect chức năng thật, không phải
-- style nit, phát hiện trong lúc review Task 2
-- (apps/cosa/models/providers.py::ModelProviderFactory._create_local_openai_compatible).
--
-- base_url là routing metadata THÔNG THƯỜNG, không phải secret (cùng loại
-- với model_id) — không thuộc phạm vi models.workspace_credentials
-- (migration 031). NULL hợp lệ cho các provider API bên thứ 3 (đã có
-- base_url cố định của chính provider đó).
--
-- Additive/Expand-only migration release (không đổi cột/ràng buộc đã có) —
-- đúng theo Encore guardrail #4.

ALTER TABLE models.model_provider_profiles
    ADD COLUMN IF NOT EXISTS base_url TEXT;
