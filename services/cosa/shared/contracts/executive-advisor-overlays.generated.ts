/**
 * GENERATED FILE — DO NOT MODIFY DIRECTLY
 * Source: shared/contracts/executive-advisor-overlays.json · Generator: scripts/gen-executive-advisor-overlays.mjs
 * To update: run scripts/sync_executive_advisor_overlays.py then node scripts/gen-executive-advisor-overlays.mjs
 */

export interface PinnedSkillIdentity {
  skillId: string;
  version: string;
  definitionHash: string;
}

export interface AdvisorOverlayDefinition {
  roleKey: string;
  overlaySpecId: string;
  overlaySpecVersion: string;
  overlayDefinitionHash: string;
  requiredProfileKey: string;
  skillPins: readonly PinnedSkillIdentity[];
  advisoryOnly: true;
}

export const ADVISOR_OVERLAY_CATALOG: Readonly<Record<string, AdvisorOverlayDefinition>> = Object.freeze({
  "chief_of_staff": Object.freeze({"roleKey":"chief_of_staff","overlaySpecId":"cosa.executive.chief_of_staff","overlaySpecVersion":"1.0.0","overlayDefinitionHash":"2dca87274c2e61cbe6fb7fab86c512f09d816c071825a86900ac7c9e9d6c704f","requiredProfileKey":"operations","skillPins":[{"skillId":"executive.board-protocol","version":"1.0.0","definitionHash":"e8fdd15bd8010c1d5636c026dd63e03d8ecf2c9165f3cce29ec839f94853ce96"},{"skillId":"executive.chief-of-staff","version":"1.0.0","definitionHash":"ee99e1b7d9bccab53d0a110abc7919e9628420ed45300196f7170bb0d3ca9a90"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "ceo": Object.freeze({"roleKey":"ceo","overlaySpecId":"cosa.executive.ceo","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"9e49f2ad24bab202d1f46b665052efeccb5902f815a8472faa59314b4336177d","requiredProfileKey":"operations","skillPins":[{"skillId":"executive.ceo-advisor","version":"1.0.0","definitionHash":"7de38afd93f98ffc285792f3ac7e2601feb452cb2af3a13c996c40757280b1a2"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cto": Object.freeze({"roleKey":"cto","overlaySpecId":"cosa.executive.cto","overlaySpecVersion":"1.2.0","overlayDefinitionHash":"e6c5ae120d9ec335a123de98bf9b01e6c72cb536ca761e138728fe6bdf6ea40a","requiredProfileKey":"coding","skillPins":[{"skillId":"executive.cto-advisor","version":"1.0.0","definitionHash":"021076c53f5be56aa07e1edbdb49afe173b6cd5368f15c4392e3aac4dd742667"},{"skillId":"engineering.workspace-site-builder","version":"1.0.0","definitionHash":"e593a2256237dd91f35c981326c11936b7ad45df74fbd67a26df171bd36e0fe0"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cfo": Object.freeze({"roleKey":"cfo","overlaySpecId":"cosa.executive.cfo","overlaySpecVersion":"1.0.0","overlayDefinitionHash":"140e55ec1140a4c0f166e26b9939c6d8f16a67fe4406fd77ee5040d31ec989a4","requiredProfileKey":"finance","skillPins":[{"skillId":"executive.cfo-advisor","version":"1.0.0","definitionHash":"52dbcc7b0dd1c6236c9dff6821739087e4904656d714ff1eb50ea99294bed3da"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cmo": Object.freeze({"roleKey":"cmo","overlaySpecId":"cosa.executive.cmo","overlaySpecVersion":"1.0.0","overlayDefinitionHash":"09eb626b040fe5aecc8c66a9c7357d2729ea2361a9d306ebe812fdfbdb6149ae","requiredProfileKey":"marketing","skillPins":[{"skillId":"executive.cmo-advisor","version":"1.0.0","definitionHash":"aa042d0f313687c2f225ce5bff34ee8704615ddff55c2dbd7a054afa9aaea24f"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "coo": Object.freeze({"roleKey":"coo","overlaySpecId":"cosa.executive.coo","overlaySpecVersion":"1.0.0","overlayDefinitionHash":"3eabe10f74a545a8f3b3f54c434e2277979ec36dd8ecb3d13791a960b42515a4","requiredProfileKey":"operations","skillPins":[{"skillId":"executive.coo-advisor","version":"1.0.0","definitionHash":"b17c6f6bf6c4931241d0f6a410dd0090531f02c83d6eecae08159f2e8cf870c3"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cro": Object.freeze({"roleKey":"cro","overlaySpecId":"cosa.executive.cro","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"55b0df2e6bdde7cbb3ad4a86122639514adfb262d06eff4eba9dc7598cbd1f75","requiredProfileKey":"sales","skillPins":[{"skillId":"executive.cro-advisor","version":"1.0.0","definitionHash":"c772513824907d8a61f02dc8af40ca6e34a74f3230126c46e44b36fe68c77db2"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cpo": Object.freeze({"roleKey":"cpo","overlaySpecId":"cosa.executive.cpo","overlaySpecVersion":"1.2.0","overlayDefinitionHash":"7c342646354d613e27429fbda92f6ba9ebf128e5d29bcb376069b9c96ba59efb","requiredProfileKey":"product","skillPins":[{"skillId":"executive.cpo-advisor","version":"1.0.0","definitionHash":"39973d3d3bd616c8c9653fa2a722ae080d317441406c2e33153ea89c2bed18be"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cco": Object.freeze({"roleKey":"cco","overlaySpecId":"cosa.executive.cco","overlaySpecVersion":"1.0.0","overlayDefinitionHash":"62159f18496512a9d579340ddc8938ffe8ee6d80711046cb8dcd1fe11af7145a","requiredProfileKey":"customer_support","skillPins":[{"skillId":"executive.cco-advisor","version":"1.0.0","definitionHash":"ef0f9d4ebc726a725dde5260b175acafca529755ac0522ea7967d5fe74a2c1eb"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "chro": Object.freeze({"roleKey":"chro","overlaySpecId":"cosa.executive.chro","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"7c8d6f5bfd4aea9904ceeb38d1139ebb00750e7a9f84c8179e5e64eb17d47c5c","requiredProfileKey":"people","skillPins":[{"skillId":"executive.chro-advisor","version":"1.0.0","definitionHash":"bb5d73d7fc6f7ebe5963417c6d2df3782580be0a3798d1a24e7b88758e8643c8"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "ciso": Object.freeze({"roleKey":"ciso","overlaySpecId":"cosa.executive.ciso","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"e8aa3cd94921fcee6368af9c8fdbf5943761fd10a4299bd5d3fd2f93c22ff8f3","requiredProfileKey":"security","skillPins":[{"skillId":"executive.ciso-advisor","version":"1.0.0","definitionHash":"49a4d6a46ed6b0437b7730b7e091c0fe84691e0d9545b663fbfbe0a7494d7485"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "gc": Object.freeze({"roleKey":"gc","overlaySpecId":"cosa.executive.gc","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"b4f226749311d6be54c9db05e7a08d3427895e25b3f06e3ff0441c5ec6e8f13b","requiredProfileKey":"legal","skillPins":[{"skillId":"executive.gc-advisor","version":"1.0.0","definitionHash":"5cedb3d84ba6263aac8ff948c091416db68d2aebaa82d5ea576984cdd4cabca5"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "cdo": Object.freeze({"roleKey":"cdo","overlaySpecId":"cosa.executive.cdo","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"944f76d4f8780baf1216d12d70adcb8211e877548d4fa936df5d33d0489fb9a8","requiredProfileKey":"data","skillPins":[{"skillId":"executive.cdo-advisor","version":"1.0.0","definitionHash":"98224cb8380143c6a9f2bd60c14620bb040ba9f8b8c1236b0f9518fe49c8ccad"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "caio": Object.freeze({"roleKey":"caio","overlaySpecId":"cosa.executive.caio","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"ad7b4872d29543d6b5cff850d00abcfa2fd6721009cd6c950946fad2c07dd8a3","requiredProfileKey":"ai_governance","skillPins":[{"skillId":"executive.caio-advisor","version":"1.0.0","definitionHash":"7431268b12a450b3158461a770f0cd25b5fa72e038c327fd774e7226344d6bdb"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
  "vpe": Object.freeze({"roleKey":"vpe","overlaySpecId":"cosa.executive.vpe","overlaySpecVersion":"1.1.0","overlayDefinitionHash":"126fddd5ef7284482aff798910efc82b2105bacfac46947d6cb453685a3844a5","requiredProfileKey":"coding","skillPins":[{"skillId":"executive.vpe-advisor","version":"1.0.0","definitionHash":"865c8411d9c2ec11e67f5f522d6abf046117cc9a590fb56a5bc99d94c3f463cf"}],"advisoryOnly":true} as AdvisorOverlayDefinition),
});
