-- Migration 032 Rollback
ALTER TABLE models.model_provider_profiles
    DROP COLUMN IF EXISTS base_url;
