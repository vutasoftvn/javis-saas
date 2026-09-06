-- Migration 46 down: Drop bsc_focus_scopes and strategic_objectives

DROP TABLE IF EXISTS strategy.bsc_focus_scopes;
DROP TABLE IF EXISTS strategy.strategic_objectives;
