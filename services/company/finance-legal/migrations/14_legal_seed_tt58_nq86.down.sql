-- services/company/finance-legal/migrations/14_legal_seed_tt58_nq86.down.sql
DELETE FROM legal.regulation_sources WHERE number IN ('58/2026/TT-BTC', '86/NQ-CP');
