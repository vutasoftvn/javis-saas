-- services/company/operations/migrations/22_weekly_reviews.down.sql
DROP INDEX IF EXISTS strategy.idx_weekly_reviews_ws_date;
DROP TABLE IF EXISTS strategy.weekly_reviews CASCADE;
