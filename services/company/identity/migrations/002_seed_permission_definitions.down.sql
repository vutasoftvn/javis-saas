-- Rollback for 002_seed_permission_definitions.up.sql
DELETE FROM core.permission_definitions WHERE permission_key IN (
  'permissions.read','permissions.manage','agent.policy.manage','agent.sweep.manage',
  'execution.plan.approve','strategy.read','strategy.write','strategy.target.manage',
  'strategy.transition','strategy.framework.manage','strategy.okr.publish',
  'strategy.initiative.approve','strategy.review.close','strategy.agent.configure',
  'finance.read','finance.transaction.record','finance.request.create',
  'finance.request.approve','finance.reconcile','finance.period.close','finance.report.read',
  'legal.read','legal.obligation.manage',
  'ai.deployment.create','ai.deployment.review','ai.deployment.approve'
);
