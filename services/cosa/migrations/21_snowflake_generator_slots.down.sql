-- services/cosa/migrations/21_snowflake_generator_slots.down.sql
DROP TABLE IF EXISTS control_plane.snowflake_generator_slots;
DROP SEQUENCE IF EXISTS control_plane.snowflake_fencing_seq;
