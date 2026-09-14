import { describe, it, expect } from "vitest";
import {
  roleKeysForStage,
  PERSISTENT_EXECUTIVE_ROLES,
  STAGE_ROLE_PRESETS,
} from "../services/executive-board-stage-presets";
import { PROJECT_LIFECYCLE_STAGES } from "../services/project-lifecycle.service";

describe("executive board stage presets", () => {
  it("maps P0_DISCOVERY to chief_of_staff, cfo, cmo, cpo", () => {
    expect(roleKeysForStage("P0_DISCOVERY")).toEqual(["chief_of_staff", "cfo", "cmo", "cpo"]);
  });

  it("maps P4_GO_TO_MARKET to cro, cco", () => {
    expect(roleKeysForStage("P4_GO_TO_MARKET")).toEqual(["cro", "cco"]);
  });

  it("returns empty array for unknown stage", () => {
    expect(roleKeysForStage("UNKNOWN")).toEqual([]);
  });

  it("persistent roles are exactly chief_of_staff/cfo/cmo/cpo", () => {
    expect([...PERSISTENT_EXECUTIVE_ROLES].sort()).toEqual([
      "cfo",
      "chief_of_staff",
      "cmo",
      "cpo",
    ]);
  });

  it("covers every one of the 7 real Project lifecycle stages", () => {
    // Chống lệch hằng số: preset phải phủ đúng tập stage thật, không tự bịa.
    for (const stage of PROJECT_LIFECYCLE_STAGES) {
      expect(roleKeysForStage(stage).length).toBeGreaterThan(0);
    }
    expect(Object.keys(STAGE_ROLE_PRESETS).sort()).toEqual([...PROJECT_LIFECYCLE_STAGES].sort());
  });
});
