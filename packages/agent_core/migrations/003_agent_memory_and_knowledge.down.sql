-- Rollback 003_agent_memory_and_knowledge.sql
DROP TABLE IF EXISTS knowledge.knowledge_chunks CASCADE;
DROP TABLE IF EXISTS knowledge.knowledge_sources CASCADE;
DROP TABLE IF EXISTS agent_memory.agent_memories CASCADE;
