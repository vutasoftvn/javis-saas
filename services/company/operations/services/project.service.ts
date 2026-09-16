import { APIError } from "encore.dev/api";
import { eq, desc, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assertLifecyclePrivileged } from "../strategy/services/lifecycle-authorization.service";
import { PROJECT_LIFECYCLE_STAGES } from "./project-lifecycle.service";
import { ensureProjectStartupTeam } from "./project-startup-team.service";
import { bootstrapP0CoreForProject } from "./p0-core-bootstrap.service";

const { projects, projectLifecycleEvents } = schema;

export interface Project {
  id: string;
  workspaceId: string;
  title: string;
  description?: string | null;
  lifecycleStage: string;
  // Task 13 (frontend) — trước đây bị bỏ sót khỏi response dù cột DB luôn
  // NOT NULL: UI cần stageVersion để bind CAS `expectedStageVersion` khi gọi
  // PATCH .../lifecycle (project-lifecycle.service.ts) mà không phải đoán 0.
  stageVersion: number;
  stageEnteredAt?: string | null;
  status: string;
  ownerMemberId?: string | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
}

// M4 §3 / 2026-09-14 remediation — Project sinh ra theo đúng 1 trong 2 mode
// tường minh: "NEW" (khởi tạo greenfield, luôn P0) hoặc "ONBOARD_EXISTING"
// (Founder khai báo baseline thật cho công ty đã tồn tại — chỉ 1 lần, có
// rationale, ghi sự kiện PROJECT_INITIALIZED). Không còn free-form
// `lifecycleStage` để client tự bịa stage bất kỳ khi tạo Project.
export type ProjectCreationMode = "NEW" | "ONBOARD_EXISTING";

export interface CreateProjectRequest {
  title: string;
  description?: string | null;
  creationMode?: ProjectCreationMode;
  // string (không phải ProjectLifecycleStage) — cùng quy ước với
  // TransitionProjectLifecycleInput.toStage: validate runtime theo
  // PROJECT_LIFECYCLE_STAGES bên trong createProjectService, không siết kiểu
  // literal union ở boundary interface.
  initialLifecycleStage?: string;
  initializationRationale?: string;
  ownerMemberId?: string | number | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: string | number | null;
  startDate?: string | null;
  endDate?: string | null;
}

function toProject(row: typeof projects.$inferSelect): Project {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    description: row.description,
    lifecycleStage: row.lifecycleStage,
    stageVersion: row.stageVersion,
    stageEnteredAt: row.stageEnteredAt ? row.stageEnteredAt.toISOString() : null,
    status: row.status,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    projectType: row.projectType,
    strategicPriority: row.strategicPriority,
    portfolioId: row.portfolioId ? row.portfolioId.toString() : null,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createProjectService(ctx: TenantContext, req: CreateProjectRequest): Promise<Project> {
  if (!req.title) {
    throw APIError.invalidArgument("title is required");
  }

  const creationMode: ProjectCreationMode = req.creationMode ?? "NEW";

  // P0 Core chỉ tự materialize khi người tạo là Founder/co-founder; đường tạo
  // Project hiện hữu cho member được giữ tương thích và không vô tình cấp
  // quyền Workspace Office. Founder có thể repair P0 project cũ bằng lệnh
  // tường minh trên Board.
  const shouldBootstrapP0Core =
    creationMode === "NEW" &&
    !ctx.isAiAgent &&
    ["founder", "co-founder"].includes((ctx.membershipRole || "").toLowerCase());

  // "ONBOARD_EXISTING" là hành động Founder xác nhận baseline P thật cho một
  // công ty đã hoạt động — validate ĐẦY ĐỦ trước khi ghi bất cứ gì (Founder/
  // co-founder authority + stage hợp lệ + rationale không rỗng), tránh ghi
  // nửa chừng rồi mới phát hiện lỗi.
  let initialStage: string = "P0_DISCOVERY";
  if (creationMode === "ONBOARD_EXISTING") {
    assertLifecyclePrivileged(ctx.membershipRole, "onboardExistingProject");

    if (
      !req.initialLifecycleStage ||
      !(PROJECT_LIFECYCLE_STAGES as readonly string[]).includes(req.initialLifecycleStage)
    ) {
      throw APIError.invalidArgument(
        `initialLifecycleStage phải là một trong ${PROJECT_LIFECYCLE_STAGES.join(", ")}`
      );
    }
    if (!req.initializationRationale || req.initializationRationale.trim().length === 0) {
      throw APIError.invalidArgument("initializationRationale là bắt buộc khi onboard project đã tồn tại");
    }
    initialStage = req.initialLifecycleStage;
  }

  const wsId = BigInt(ctx.workspaceId);

  const row = await db.transaction(async (tx) => {
    const [p] = await tx
      .insert(projects)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        title: req.title,
        description: req.description || null,
        // M4 §3 — "NEW" luôn P0_DISCOVERY; "ONBOARD_EXISTING" dùng đúng baseline
        // Founder khai báo. Project stage độc lập Workspace.
        lifecycleStage: initialStage,
        // "ONBOARD_EXISTING" ghi nhận baseline này bằng 1 event PROJECT_INITIALIZED
        // (fromStage NULL) nên stageVersion bắt đầu ở 1 — không phải transition từ
        // P0, tránh bịa lịch sử "đã từng ở P0 rồi mới lên P4".
        stageVersion: creationMode === "ONBOARD_EXISTING" ? 1 : 0,
        stageEnteredAt: new Date(),
        ownerMemberId: req.ownerMemberId ? BigInt(req.ownerMemberId) : null,
        projectType: req.projectType || "STRATEGIC",
        strategicPriority: req.strategicPriority || "P1",
        portfolioId: req.portfolioId ? BigInt(req.portfolioId) : null,
        startDate: req.startDate ? new Date(req.startDate) : null,
        endDate: req.endDate ? new Date(req.endDate) : null,
      })
      .returning();

    if (!p) throw APIError.internal("Failed to create project");

    if (creationMode === "ONBOARD_EXISTING") {
      // Append-only, event_type riêng khỏi 'TRANSITION' — fromStage NULL vì đây
      // là khai báo baseline, không phải một bước chuyển từ P0 thật.
      await tx.insert(projectLifecycleEvents).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: p.id,
        eventType: "PROJECT_INITIALIZED",
        fromStage: null,
        toStage: initialStage,
        fromStageVersion: 0,
        actorMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        rationale: req.initializationRationale ?? null,
        initializationSource: "FOUNDER_ONBOARDING",
      });
    }

    await ensureProjectStartupTeam(tx, {
      workspaceId: ctx.workspaceId,
      projectId: p.id.toString(),
      actorId: ctx.userId ?? ctx.workspaceId,
    });

    return p;
  });

  // NEW luôn bắt đầu P0 và có bốn role P0 Core hoạt động ngay. Hàm bootstrap
  // hội tụ/idempotent: nếu một lỗi hạ tầng xảy ra sau khi Project đã commit,
  // Founder có thể chạy lại lệnh explicit trên Board để hoàn tất đúng phần còn
  // thiếu, không cần tạo một Project khác.
  if (shouldBootstrapP0Core) {
    await bootstrapP0CoreForProject(ctx, row.id.toString());
  }

  return toProject(row);
}

export async function getProjectService(ctx: TenantContext, id: string | number): Promise<Project> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, BigInt(id)), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!row) throw APIError.notFound("Project not found");
  return toProject(row);
}

export async function listProjectsService(ctx: TenantContext): Promise<Project[]> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(projects)
    .where(eq(projects.workspaceId, wsId))
    .orderBy(desc(projects.id));

  return rows.map(toProject);
}
