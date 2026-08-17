---
domain: cosa
name: chief_of_staff_synthesis
version: 1.0.0
description: Synthesis prompt for Chief of Staff to diagnose founder goal based on sales and finance snapshot.
tags: [chief_of_staff, synthesis, strategy]
---
Founder goal: ${goal}

Real sales pipeline snapshot: ${sales_data}
Real finance snapshot: ${fin_data}

Diagnose the situation strictly from the data above and answer the Founder's goal. Respond as a single JSON object:
{"diagnosis": "<2-4 sentence analysis grounded in the data above>"}. Do not invent numbers not present in the snapshots above.
