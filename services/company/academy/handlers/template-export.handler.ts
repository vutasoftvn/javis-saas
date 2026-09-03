/**
 * Academy template export handler.
 *
 * ISOLATION RULE: This file MUST NOT import any module from:
 * - `operations/strategy` handlers or services
 * - `operations/handlers` (project, task, etc.)
 * - `commercial` or `finance-legal` handlers
 *
 * A template export is the ONLY sanctioned one-way path from Academy to a
 * live workspace. It never produces Evidence, a source-ingestion record, a
 * gate input, a metric snapshot, or a task.
 */
import { api } from "encore.dev/api";
import {
  exportTemplate as exportTemplateImpl,
  getTemplateExport as getTemplateExportImpl,
} from "../services/template_export.service";
import type { AcademyTemplateExport, ExportTemplateParams } from "../services/template_export.service";

export type { AcademyTemplateExport, ExportTemplateParams };

// Giữ nguyên tên export `exportTemplate`/`getTemplateExport` (thay vì hậu tố
// `Endpoint`) để không phá vỡ các nơi gọi trực tiếp hàm api()-wrapped trong
// test — cùng cách `createProject` được export trực tiếp ở project.handler.ts.
export const exportTemplate = api(
  { method: "POST", path: "/academy/template-exports", expose: true },
  async (params: ExportTemplateParams): Promise<AcademyTemplateExport> => exportTemplateImpl(params)
);

export const getTemplateExport = api(
  { method: "GET", path: "/academy/template-exports/:id", expose: true },
  async ({ id }: { id: string }): Promise<AcademyTemplateExport> => getTemplateExportImpl(id)
);
