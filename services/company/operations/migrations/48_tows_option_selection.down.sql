-- Migration 48 down: Drop tows_option_evaluations and tows_options

DROP TABLE IF EXISTS strategy.tows_option_evaluations;
DROP TABLE IF EXISTS strategy.tows_options;
