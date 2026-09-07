ALTER TABLE cosa.profiles
  ADD COLUMN preferred_locale VARCHAR(10) NOT NULL DEFAULT 'vi-VN';

ALTER TABLE cosa.profiles
  ADD CONSTRAINT chk_profiles_preferred_locale CHECK (preferred_locale IN ('vi-VN', 'en-US'));

UPDATE cosa.profiles
  SET preferred_locale = 'vi-VN'
  WHERE preferred_locale IS NULL;
