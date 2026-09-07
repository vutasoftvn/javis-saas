ALTER TABLE cosa.profiles
  DROP CONSTRAINT IF EXISTS chk_profiles_preferred_locale;

ALTER TABLE cosa.profiles
  DROP COLUMN IF EXISTS preferred_locale;
