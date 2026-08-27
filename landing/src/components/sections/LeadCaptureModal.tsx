"use client";

import React, { useState } from "react";
import { X, Sparkles, User, Mail, Phone, Building, CheckCircle2, ArrowRight } from "lucide-react";

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
    source: initialSource,
  });

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      try {
        await fetch("/api/v1/marketing/public/forms/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            form_id: "landing-modal-lead",
            data: { ...formData, source: initialSource },
          }),
        });
      } catch {
        console.log("[Modal Lead Captured]:", formData);
      }

      await new Promise((r) => setTimeout(r, 800));
      setSubmitted(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-3xl bg-[#080f1e] border border-cosa-cyan/40 p-6 sm:p-8 shadow-[0_0_60px_rgba(0,240,255,0.25)]">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full bg-[#0d172a] text-slate-400 hover:text-white border border-slate-700 hover:border-cosa-cyan transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {submitted ? (
          <div className="py-8 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-cosa-emerald/20 border border-cosa-emerald text-cosa-emerald mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-bold text-white">Yêu Cầu Đã Được Tiếp Nhận!</h3>
            <p className="text-xs text-slate-300">
              Đội ngũ kỹ sư của COSA OS sẽ liên hệ hỗ trợ triển khai demo trong thời gian sớm nhất.
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 rounded-xl bg-gradient-to-r from-cosa-cyan to-cosa-blue text-slate-950 font-bold text-xs"
            >
              Đóng Cửa Sổ
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cosa-cyan/10 text-cosa-cyan text-[10px] font-mono border border-cosa-cyan/30 mb-2">
                <Sparkles className="w-3 h-3" />
                <span>COSA OS 13.2 DEMO ACTIVATION</span>
              </div>
              <h3 className="text-xl font-bold text-white">Đăng Ký Trải Nghiệm COSA OS</h3>
              <p className="text-xs text-slate-400 mt-1">
                Kích hoạt tài khoản dùng thử 14 ngày kèm buổi demo 1-on-1 từ chuyên gia.
              </p>
            </div>

            <div className="space-y-3 pt-2">
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
                  Email doanh nghiệp *
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
                    placeholder="name@company.com"
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
                    Tên công ty *
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
                      placeholder="TechCorp"
                      className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-xs text-white placeholder-slate-600 transition-all"
                    />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 py-3 rounded-xl font-bold text-xs text-slate-950 bg-gradient-to-r from-cosa-cyan to-cosa-blue hover:from-white hover:to-cosa-cyan shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all flex items-center justify-center gap-2 transform active:scale-95 disabled:opacity-50"
            >
              {loading ? (
                <span>Đang xử lý...</span>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Xác Nhận & Nhận Tư Vấn Trực Tiếp</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
