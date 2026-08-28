-- Rollback 006_conversation_substrate.sql
DROP TABLE IF EXISTS agent_conversation.messages CASCADE;
DROP TABLE IF EXISTS agent_conversation.conversations CASCADE;
