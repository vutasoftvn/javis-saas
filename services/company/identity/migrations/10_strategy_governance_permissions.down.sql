DELETE FROM core.permission_definitions
WHERE permission_key IN (
  'strategy.framework.manage',
  'strategy.analysis.write',
  'strategy.option.select',
  'strategy.okr.publish',
  'strategy.initiative.approve',
  'strategy.review.close',
  'strategy.agent.configure'
);
