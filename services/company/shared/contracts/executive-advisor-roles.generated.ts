/**
 * GENERATED FILE — DO NOT MODIFY DIRECTLY
 * Source: shared/contracts/executive-advisor-roles.json · Generator: scripts/gen-executive-advisor-roles.mjs
 * To update: edit shared/contracts/executive-advisor-roles.json and run `node scripts/gen-executive-advisor-roles.mjs`
 */

export type StartupCorePresetKey = 'startup-discovery' | 'startup-build-launch';

export type ExecutiveRoleKey =
  | "chief_of_staff"
  | "ceo"
  | "cto"
  | "cfo"
  | "cmo"
  | "coo"
  | "cro"
  | "cpo"
  | "cco"
  | "chro"
  | "ciso"
  | "gc"
  | "cdo"
  | "caio"
  | "vpe";

export type ExecutiveRuntimeReadiness =
  | 'READY'
  | 'PENDING_OPERATIONS_PROFILE'
  | 'PENDING_SALES_PROFILE'
  | 'PENDING_PRODUCT_PROFILE'
  | 'PENDING_CUSTOMER_SUPPORT_PROFILE'
  | 'PENDING_PEOPLE_PROFILE'
  | 'PENDING_SECURITY_PROFILE'
  | 'PENDING_LEGAL_PROFILE'
  | 'PENDING_DATA_PROFILE'
  | 'PENDING_AI_GOVERNANCE_PROFILE'
  | 'PENDING_ENGINEERING_PROFILE';

export const EXECUTIVE_ROLE_KEYS = [
  "chief_of_staff",
  "ceo",
  "cto",
  "cfo",
  "cmo",
  "coo",
  "cro",
  "cpo",
  "cco",
  "chro",
  "ciso",
  "gc",
  "cdo",
  "caio",
  "vpe",
] as const;

export const STARTUP_CORE_PRESET_KEYS = [
  "startup-discovery",
  "startup-build-launch",
] as const;

export interface ExecutiveAdvisorRoleDef {
  key: ExecutiveRoleKey;
  label: string;
  advisoryRemit: string;
  requiredProfileKey: string;
  requiredAgentSpec: string;
  requiredSkillPins: readonly string[];
  advisoryOnly: boolean;
  runtimeReadiness: ExecutiveRuntimeReadiness;
  sourceProvenance: string;
}

export interface StartupCorePresetDef {
  key: StartupCorePresetKey;
  label: string;
  description: string;
  defaultRoleKeys: readonly ExecutiveRoleKey[];
}

export const EXECUTIVE_ROLE_CATALOG: Readonly<Record<ExecutiveRoleKey, ExecutiveAdvisorRoleDef>> = Object.freeze({
  "chief_of_staff": Object.freeze({"key":"chief_of_staff","label":"Chief of Staff","advisoryRemit":"Deliberation framing, cross-functional routing, synthesis, decision-log hygiene","requiredProfileKey":"operations","requiredAgentSpec":"cosa.executive.chief_of_staff","requiredSkillPins":["skillpack:executive/board-protocol@1.0.0","skillpack:executive/chief-of-staff@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "ceo": Object.freeze({"key":"ceo","label":"Chief Executive Officer / Strategic Advisor","advisoryRemit":"Vision alignment, capital allocation, strategic trade-offs, board governance, stage-adaptive growth","requiredProfileKey":"operations","requiredAgentSpec":"cosa.executive.ceo","requiredSkillPins":["skillpack:executive/ceo-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cto": Object.freeze({"key":"cto","label":"Chief Technology Officer / Technical Strategy Advisor","advisoryRemit":"Technology vision, system architecture, hybrid engineering workforce, tech debt governance, build vs buy evaluation","requiredProfileKey":"coding","requiredAgentSpec":"cosa.executive.cto","requiredSkillPins":["skillpack:executive/cto-advisor@1.0.0","skillpack:engineering/workspace-site-builder@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cfo": Object.freeze({"key":"cfo","label":"Chief Financial Officer","advisoryRemit":"Cash runway, scenario modeling, budget guardrails, unit economics","requiredProfileKey":"finance","requiredAgentSpec":"cosa.executive.cfo","requiredSkillPins":["skillpack:executive/cfo-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cmo": Object.freeze({"key":"cmo","label":"Chief Marketing Officer","advisoryRemit":"Positioning, demand generation, messaging, growth experiment strategy","requiredProfileKey":"marketing","requiredAgentSpec":"cosa.executive.cmo","requiredSkillPins":["skillpack:executive/cmo-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "coo": Object.freeze({"key":"coo","label":"Chief Operating Officer","advisoryRemit":"Operational cadence, process constraints, delivery dependency mapping","requiredProfileKey":"operations","requiredAgentSpec":"cosa.executive.coo","requiredSkillPins":["skillpack:executive/coo-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cro": Object.freeze({"key":"cro","label":"Chief Revenue Officer","advisoryRemit":"Revenue pipeline, sales enablement, pricing guardrails, RevOps alignment","requiredProfileKey":"sales","requiredAgentSpec":"cosa.executive.cro","requiredSkillPins":["skillpack:executive/cro-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cpo": Object.freeze({"key":"cpo","label":"Chief Product Officer","advisoryRemit":"Customer problem validation, product bets, PRD and backlog priority review","requiredProfileKey":"product","requiredAgentSpec":"cosa.executive.cpo","requiredSkillPins":["skillpack:executive/cpo-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cco": Object.freeze({"key":"cco","label":"Chief Customer Officer","advisoryRemit":"Customer retention, lifecycle health, support pattern learning","requiredProfileKey":"customer_support","requiredAgentSpec":"cosa.executive.cco","requiredSkillPins":["skillpack:executive/cco-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "chro": Object.freeze({"key":"chro","label":"Chief Human Resources Officer","advisoryRemit":"Organizational design, hiring process evaluation, team and people risk","requiredProfileKey":"people","requiredAgentSpec":"cosa.executive.chro","requiredSkillPins":["skillpack:executive/chro-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "ciso": Object.freeze({"key":"ciso","label":"Chief Information Security Officer","advisoryRemit":"Security threat modeling, privacy controls, compliance gap assessment","requiredProfileKey":"security","requiredAgentSpec":"cosa.executive.ciso","requiredSkillPins":["skillpack:executive/ciso-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "gc": Object.freeze({"key":"gc","label":"General Counsel","advisoryRemit":"Legal and regulatory issue spotting, policy risk resolution, escalation","requiredProfileKey":"legal","requiredAgentSpec":"cosa.executive.gc","requiredSkillPins":["skillpack:executive/gc-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "cdo": Object.freeze({"key":"cdo","label":"Chief Data Officer","advisoryRemit":"Data governance, quality, rights management, scoped knowledge integrity","requiredProfileKey":"data","requiredAgentSpec":"cosa.executive.cdo","requiredSkillPins":["skillpack:executive/cdo-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "caio": Object.freeze({"key":"caio","label":"Chief AI Officer","advisoryRemit":"Model evaluation, provider governance, prompt safety, red-team assessment","requiredProfileKey":"ai_governance","requiredAgentSpec":"cosa.executive.caio","requiredSkillPins":["skillpack:executive/caio-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
  "vpe": Object.freeze({"key":"vpe","label":"VP Engineering","advisoryRemit":"Technical feasibility, architecture constraints, release readiness, delivery risks","requiredProfileKey":"coding","requiredAgentSpec":"cosa.executive.vpe","requiredSkillPins":["skillpack:executive/vpe-advisor@1.0.0"],"advisoryOnly":true,"runtimeReadiness":"READY","sourceProvenance":"superpowers:executive-advisory-board"} as unknown as ExecutiveAdvisorRoleDef),
});

export const STARTUP_CORE_PRESETS: Readonly<Record<StartupCorePresetKey, StartupCorePresetDef>> = Object.freeze({
  "startup-discovery": Object.freeze({"key":"startup-discovery","label":"Startup Discovery Core","description":"Giữ focus quyết định, kiểm chứng nhu cầu/thông điệp và kiểm soát runway sớm.","defaultRoleKeys":["chief_of_staff","cmo","cfo"]} as unknown as StartupCorePresetDef),
  "startup-build-launch": Object.freeze({"key":"startup-build-launch","label":"Startup Build & Launch Core","description":"Bổ sung điều phối vận hành khi Founder đã chủ động vào giai đoạn build/launch.","defaultRoleKeys":["chief_of_staff","cmo","cfo","coo"]} as unknown as StartupCorePresetDef),
});

export function isExecutiveRoleKey(val: unknown): val is ExecutiveRoleKey {
  return typeof val === 'string' && (EXECUTIVE_ROLE_KEYS as readonly string[]).includes(val);
}

export function isStartupCorePresetKey(val: unknown): val is StartupCorePresetKey {
  return typeof val === 'string' && (STARTUP_CORE_PRESET_KEYS as readonly string[]).includes(val);
}
