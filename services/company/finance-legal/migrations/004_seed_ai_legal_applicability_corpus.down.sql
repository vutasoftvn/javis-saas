-- Gỡ đúng các row do 004_seed_ai_legal_applicability_corpus.up.sql seed, theo id.
-- Thứ tự con → cha để không vướng FK (rule → version → source).

DELETE FROM legal.ai_applicability_rules WHERE id IN (301, 302, 303, 304, 305, 306);
DELETE FROM legal.regulation_versions WHERE id IN (210, 211, 212, 213, 214, 215, 216, 217, 218);
DELETE FROM legal.regulation_sources WHERE id IN (2, 10, 11, 12, 13, 14, 15, 16, 17);
