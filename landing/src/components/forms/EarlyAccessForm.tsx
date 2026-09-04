"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  Building,
  Mail,
  Phone,
  User,
  ArrowRight,
  Info,
  AlertCircle,
} from "lucide-react";
import { PersonaDiscoveryWizard } from "../sections/PersonaDiscoveryWizard";

export interface EarlyAccessFormData {
  fullName: string;
  email: string;
  phone: string;
  userSegment: string;
  projectName: string;
  note?: string;
}

export interface EarlyAccessSubmitResult {
  accessCode: string;
  email: string;
  userSegment: string;
  projectName: string;
}

export interface EarlyAccessFormProps {
  variant?: "full" | "modal" | "inline";
  initialSource?: string;
  showFreePolicyBanner?: boolean;
  autoTransitionToPersonaWizard?: boolean;
  onSuccess?: (result: EarlyAccessSubmitResult) => void;
  onClose?: () => void;
  className?: string;
}

export const USER_SEGMENT_OPTIONS = [
  { value: "Học sinh, Sinh viên / Nghiên cứu học tập", label: "🎓 Học sinh, Sinh viên / Nghiên cứu học tập" },
  { value: "OPC (Doanh nghiệp 1 người) / Solo Creator", label: "👤 OPC (Doanh nghiệp 1 người) / Solo Creator" },
  { value: "Startup / Đội ngũ tinh gọn (2 - 15 nhân sự)", label: "🚀 Startup / Đội ngũ tinh gọn (2 - 15 nhân sự)" },
  { value: "Doanh nghiệp vừa & lớn (> 15 nhân sự)", label: "🏢 Doanh nghiệp vừa & lớn (> 15 nhân sự)" },
];

export const FreeTierPolicyNotice: React.FC<{ compact?: boolean }> = ({ compact }) => (
  <div
    className={`rounded-2xl bg-cosa-cyan/5 border border-cosa-cyan/30 flex items-start gap-2.5 ${
      compact ? "p-3" : "p-3.5"
    }`}
  >
    <Info className="w-4 h-4 text-cosa-cyan shrink-0 mt-0.5" />
    <p className="text-xs text-slate-300 leading-relaxed">
      <strong className="text-cosa-cyan">Chính sách Gói Free:</strong> Mỗi tài khoản được khởi tạo tối đa{" "}
      <strong>01 Workspace</strong> &amp; <strong>01 Project</strong>. Miễn phí 100% 0đ trọn đời cho phân tích dự án &amp; người dùng.
    </p>
  </div>
);

export const EarlyAccessForm: React.FC<EarlyAccessFormProps> = ({
  variant = "full",
  initialSource = "general_cta",
  showFreePolicyBanner = true,
  autoTransitionToPersonaWizard = true,
  onSuccess,
  onClose,
  className = "",
}) => {
  const [formData, setFormData] = useState<EarlyAccessFormData>({
    fullName: "",
    email: "",
    phone: "",
    userSegment: USER_SEGMENT_OPTIONS[1].value,
    projectName: "",
    note: "",
  });

  const [loading, setLoading] = useState(false);
  const [submittedData, setSubmittedData] = useState<EarlyAccessSubmitResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isModal = variant === "modal";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);

    try {
      const payload = {
        fullName: formData.fullName,
        email: formData.email,
        phone: formData.phone,
        company: formData.projectName.trim() || formData.userSegment,
        userSegment: formData.userSegment,
        projectName: formData.projectName,
        priorityInterest: "Gói Free - 1 Workspace & 1 Project",
        note: formData.note || `Nguồn đăng ký: ${initialSource}`,
      };

      const res = await fetch("/api/early-access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Không thể xử lý đăng ký lúc này. Vui lòng thử lại sau.");
      }

      const result: EarlyAccessSubmitResult = {
        accessCode: data.accessCode,
        email: formData.email,
        userSegment: formData.userSegment,
        projectName: formData.projectName.trim() || "Dự án mới",
      };

      setSubmittedData(result);
      if (onSuccess) onSuccess(result);
    } catch (err: unknown) {
      console.error("[Early Access Form Error]:", err);
      const msg = err instanceof Error ? err.message : "Đã xảy ra lỗi kết nối. Vui lòng thử lại.";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSubmittedData(null);
    setErrorMessage(null);
  };

  if (submittedData && autoTransitionToPersonaWizard) {
    return (
      <div className={`space-y-6 ${className}`}>
        {/* Confirmation Header Badge */}
        <div className="p-3.5 sm:p-4 rounded-2xl bg-[#04070e] border border-cosa-emerald/40 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-cosa-emerald/20 border border-cosa-emerald flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-5 h-5 text-cosa-emerald" />
            </div>
            <div className="text-left">
              <div className="text-[11px] font-mono font-bold text-cosa-emerald uppercase">
                ĐÃ GHI NHẬN SUẤT TRẢI NGHIỆM SỚM
              </div>
              <div className="text-xs text-white font-medium">
                {submittedData.email} · {submittedData.userSegment}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-slate-500 hover:text-slate-300 font-mono transition-colors"
          >
            Đăng ký khác
          </button>
        </div>

        {/* Embedded Persona Discovery Wizard (Form 2) */}
        <PersonaDiscoveryWizard
          email={submittedData.email}
          userSegment={submittedData.userSegment}
          projectName={submittedData.projectName}
          onComplete={onClose || handleReset}
          onSkip={onClose || handleReset}
        />
      </div>
    );
  }

  return (
    <div className={`space-y-5 ${className}`}>
      {/* Form Title & Context */}
      <div className="space-y-1">
        <h3 className={`font-bold text-white ${isModal ? "text-xl" : "text-xl sm:text-2xl"}`}>
          Đăng Ký Nhận Quyền Trải Nghiệm Sớm
        </h3>
        <p className="text-xs sm:text-sm text-slate-400">
          Gói Discovery miễn phí 100% 0đ trọn đời cho phân tích dự án &amp; người dùng.
        </p>
      </div>

      {showFreePolicyBanner && <FreeTierPolicyNotice compact={isModal} />}

      {errorMessage && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Full Name & Email */}
        <div className={`grid gap-4 ${isModal ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"}`}>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Họ và tên *
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={formData.fullName}
                onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                placeholder="Nguyễn Văn A"
                className={`w-full pl-9 pr-3 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-white placeholder-slate-600 transition-all ${
                  isModal ? "py-2 text-xs" : "py-2.5 text-sm"
                }`}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Email tiếp nhận *
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="name@gmail.com hoặc edu.vn"
                className={`w-full pl-9 pr-3 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-white placeholder-slate-600 transition-all ${
                  isModal ? "py-2 text-xs" : "py-2.5 text-sm"
                }`}
              />
            </div>
          </div>
        </div>

        {/* Phone & User Segment */}
        <div className={`grid gap-4 ${isModal ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"}`}>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Số điện thoại / Zalo *
            </label>
            <div className="relative">
              <Phone className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="tel"
                required
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="0912 345 678"
                className={`w-full pl-9 pr-3 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-white placeholder-slate-600 transition-all ${
                  isModal ? "py-2 text-xs" : "py-2.5 text-sm"
                }`}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Nhóm đối tượng của bạn *
            </label>
            <select
              value={formData.userSegment}
              onChange={(e) => setFormData({ ...formData, userSegment: e.target.value })}
              className={`w-full px-3 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-white transition-all ${
                isModal ? "py-2 text-xs" : "py-2.5 text-sm"
              }`}
            >
              {USER_SEGMENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Project Name */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Tên dự án duy nhất dự kiến khởi tạo (Tùy chọn)
          </label>
          <div className="relative">
            <Building className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={formData.projectName}
              onChange={(e) => setFormData({ ...formData, projectName: e.target.value })}
              placeholder="Ví dụ: Đồ án AI 2026, Dự án SaaS X, Tên công ty..."
              className={`w-full pl-9 pr-3 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-white placeholder-slate-600 transition-all ${
                isModal ? "py-2 text-xs" : "py-2.5 text-sm"
              }`}
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 sm:py-4 rounded-xl font-bold text-xs sm:text-sm text-slate-950 bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue hover:from-white hover:to-cosa-cyan shadow-[0_0_30px_rgba(0,240,255,0.4)] transition-all flex items-center justify-center gap-2 transform active:scale-95 disabled:opacity-50"
          >
            {loading ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                <span>Đang ghi nhận vào hàng chờ ưu tiên...</span>
              </div>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-slate-950" />
                <span>Đăng Ký Nhận Quyền Trải Nghiệm Sớm</span>
                <ArrowRight className="w-4 h-4 text-slate-950" />
              </>
            )}
          </button>
        </div>

        <p className="text-[11px] text-center text-slate-500">
          Không cần thẻ tín dụng · Cam kết không spam · Xác nhận gửi tự động qua Resend API.
        </p>
      </form>
    </div>
  );
};
