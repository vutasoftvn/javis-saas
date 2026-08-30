"use client";

import React, { useState } from "react";
import {
  X,
  Sparkles,
  User,
  Mail,
  Phone,
  Building,
  CheckCircle2,
  ArrowRight,
  AlertCircle,
} from "lucide-react";

interface LeadCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialSource?: string;
}

export const LeadCaptureModal: React.FC<LeadCaptureModalProps> = ({
  isOpen,
  onClose,
  initialSource = "general_cta",
}) => {
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phone: "",
    company: "",
    role: "Founder / CEO",
    priorityInterest: "Trọn bộ Hệ điều hành COSA OS",
  });

  const [loading, setLoading] = useState(false);
  const [submittedData, setSubmittedData] = useState<{
    accessCode: string;
    email: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/early-access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          note: `Đăng ký nhanh từ modal popup (Nguồn: ${initialSource})`,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Không thể xử lý đăng ký lúc này. Vui lòng thử lại sau.");
      }

      setSubmittedData({
        accessCode: data.accessCode,
        email: formData.email,
      });
    } catch (err: unknown) {
      console.error("[Modal Early Access Error]:", err);
      const msg = err instanceof Error ? err.message : "Đã xảy ra lỗi kết nối. Vui lòng thử lại.";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleModalClose = () => {
    setSubmittedData(null);
    setErrorMessage(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-3xl bg-[#080f1e] border border-cosa-cyan/40 p-6 sm:p-8 shadow-[0_0_60px_rgba(0,240,255,0.25)]">
        {/* Close button */}
        <button
          onClick={handleModalClose}
          className="absolute top-4 right-4 p-2 rounded-full bg-[#0d172a] text-slate-400 hover:text-white border border-slate-700 hover:border-cosa-cyan transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {submittedData ? (
          <div className="py-6 text-center space-y-5 animate-fadeIn">
            <div className="w-14 h-14 rounded-full bg-cosa-emerald/20 border border-cosa-emerald text-cosa-emerald mx-auto flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.4)]">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-white">Đăng Ký Thành Công!</h3>
              <p className="text-xs text-slate-300 mt-1">
                Email xác nhận kèm hướng dẫn kích hoạt đã được gửi qua Resend tới:
              </p>
              <p className="text-sm font-semibold text-cosa-cyan mt-0.5">{submittedData.email}</p>
            </div>

            {/* VIP Pass */}
            <div className="p-4 rounded-xl bg-[#04070e] border border-cosa-cyan/40 text-left space-y-1">
              <div className="text-[10px] font-mono text-slate-400 uppercase">Mã Vé VIP Early Access</div>
              <div className="text-2xl font-bold text-cosa-cyan font-mono">{submittedData.accessCode}</div>
              <div className="text-[11px] text-slate-400 pt-1">
                Đội ngũ COSA OS sẽ liên hệ hỗ trợ bạn trong vòng 2 giờ làm việc.
              </div>
            </div>

            <button
              onClick={handleModalClose}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-cosa-cyan to-cosa-blue text-slate-950 font-bold text-xs font-mono"
            >
              Đóng Cửa Sổ
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cosa-cyan/10 text-cosa-cyan text-[10px] font-mono border border-cosa-cyan/30 mb-2">
                <Sparkles className="w-3 h-3" />
                <span>COSA OS VIP WAITLIST · CÒN 42 SUẤT</span>
              </div>
              <h3 className="text-xl font-bold text-white">Đăng Ký Quyền Dùng Sớm</h3>
              <p className="text-xs text-slate-400 mt-1">
                Gói OPC hoàn toàn miễn phí (0đ) cho giai đoạn phân tích dự án, nghiên cứu người dùng &amp; lập kế hoạch.
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="space-y-3 pt-1">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Họ và tên *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={formData.fullName}
                    onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                    placeholder="Nguyễn Văn A"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-xs text-white placeholder-slate-600 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Email công việc *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="founder@company.com"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-xs text-white placeholder-slate-600 transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Số điện thoại / Zalo *
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <Phone className="w-4 h-4" />
                    </div>
                    <input
                      type="tel"
                      required
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="0912 345 678"
                      className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-xs text-white placeholder-slate-600 transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Công ty / Dự án *
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <Building className="w-4 h-4" />
                    </div>
                    <input
                      type="text"
                      required
                      value={formData.company}
                      onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                      placeholder="Acme Corp"
                      className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-xs text-white placeholder-slate-600 transition-all"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Nhu cầu ưu tiên
                </label>
                <select
                  value={formData.priorityInterest}
                  onChange={(e) => setFormData({ ...formData, priorityInterest: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-xs text-white transition-all"
                >
                  <option value="OPC - Phân Tích Dự Án & Người Dùng (Free)">OPC - Phân Tích Dự Án &amp; Người Dùng (Miễn Phí)</option>
                  <option value="Trọn bộ Hệ điều hành COSA OS">Trọn bộ COSA OS</option>
                  <option value="Chiến Lược 12 Tuần & OKRs">Chiến Lược 12 Tuần &amp; OKRs</option>
                  <option value="Unified Workforce (AI + Human)">Nhân sự Hợp nhất (AI + Người)</option>
                  <option value="Kế Toán Thông tư 58/TT-BTC & Phê Duyệt Chi">Kế Toán Thông tư 58/TT-BTC</option>
                  <option value="Trợ Lý AI Đa Nhiệm">Trợ Lý AI Đa Nhiệm</option>
                  <option value="Bảo Mật On-Premise">Triển khai Máy chủ Riêng</option>
                </select>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 rounded-xl font-bold text-xs text-slate-950 bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue hover:from-white hover:to-cosa-cyan shadow-[0_0_25px_rgba(0,240,255,0.4)] transition-all flex items-center justify-center gap-2 transform active:scale-95 disabled:opacity-50"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                    <span>Đang Gửi Xác Nhận Qua Resend...</span>
                  </div>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-slate-950" />
                    <span>Xác Nhận & Cấp Mã VIP Early Access</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-950" />
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
