"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  Building,
  Mail,
  Phone,
  User,
  ShieldCheck,
  Zap,
  ArrowRight,
  BadgeCheck,
  AlertCircle,
  Clock
} from "lucide-react";

interface LeadFormSectionProps {
  onSuccess?: () => void;
}

export const LeadFormSection: React.FC<LeadFormSectionProps> = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phone: "",
    company: "",
    role: "Founder / CEO",
    teamSize: "5-20",
    priorityInterest: "Trọn bộ Hệ điều hành COSA OS",
    note: "",
  });

  const [loading, setLoading] = useState(false);
  const [submittedData, setSubmittedData] = useState<{
    accessCode: string;
    email: string;
    simulated?: boolean;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/early-access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Không thể xử lý đăng ký lúc này. Vui lòng thử lại sau.");
      }

      setSubmittedData({
        accessCode: data.accessCode,
        email: formData.email,
        simulated: data.emailDelivery?.simulated,
      });

      if (onSuccess) onSuccess();
    } catch (err: unknown) {
      console.error("[Submit Early Access Error]:", err);
      const msg = err instanceof Error ? err.message : "Đã xảy ra lỗi kết nối. Vui lòng thử lại.";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="contact-form" className="py-24 bg-[#070c18] relative overflow-hidden border-t border-cosa-border">
      {/* Glow Aura */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-cosa-cyan/10 blur-[180px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Value Prop */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
              <Sparkles className="w-3.5 h-3.5" />
              <span>CHƯƠNG TRÌNH TRẢI NGHIỆM SỚM · ĐỢT 1</span>
            </div>

            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
              Sẵn Sàng Chuyển Đổi Sang Mô Hình{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
                Doanh Nghiệp Tự Trị?
              </span>
            </h2>

            <p className="text-slate-300 text-base leading-relaxed">
              Trở thành 1 trong <strong className="text-white">100 nhà sáng lập đầu tiên</strong> nhận quyền truy cập đặc quyền hệ thống COSA OS, kèm buổi demo 1-on-1 cấu hình trên bài toán thực tế của doanh nghiệp bạn.
            </p>

            <div className="space-y-4 pt-2">
              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-border">
                <div className="p-2 rounded-xl bg-cosa-cyan/10 text-cosa-cyan shrink-0">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Xác Nhận Tức Thì Qua Email</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Hệ thống tự động cấp Mã Thẻ VIP Early Access và gửi thông tin xác nhận qua cổng email Resend API.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-border">
                <div className="p-2 rounded-xl bg-cosa-emerald/10 text-cosa-emerald shrink-0">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Bảo Mật Tuyệt Đối & Tự Sở Hữu Dữ Liệu</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Tùy chọn triển khai Local Data Plane Postgres trên hạ tầng máy chủ riêng của doanh nghiệp (Zero Data Retention).
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-emerald/30">
                <div className="p-2 rounded-xl bg-cosa-emerald/10 text-cosa-emerald shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Mô Hình OPC: Free Phân Tích Dự Án</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Doanh nghiệp một người được miễn phí 100% trọn đời giai đoạn khảo sát nhu cầu, chân dung người dùng và lập kế hoạch PRD.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Lead Form */}
          <div className="lg:col-span-7">
            <div className="p-8 sm:p-10 rounded-3xl bg-[#080f1e]/95 border border-cosa-cyan/30 shadow-[0_0_50px_rgba(0,240,255,0.15)] backdrop-blur-2xl">
              {submittedData ? (
                <div className="py-10 text-center space-y-6 animate-fadeIn">
                  <div className="w-16 h-16 rounded-full bg-cosa-emerald/20 border border-cosa-emerald flex items-center justify-center mx-auto shadow-[0_0_30px_rgba(16,185,129,0.5)]">
                    <CheckCircle2 className="w-8 h-8 text-cosa-emerald" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-2xl font-bold text-white">Đăng Ký Thành Công!</h3>
                    <p className="text-sm text-slate-300 max-w-md mx-auto">
                      Chào mừng bạn gia nhập chương trình Early Access của COSA OS. Mã truy cập độc quyền đã được gửi qua email.
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#04070e] border border-slate-800 max-w-md mx-auto text-left space-y-2 text-xs font-mono">
                    <div className="text-slate-500">MÃ THẺ EARLY ACCESS CỦA BẠN:</div>
                    <div className="text-cosa-cyan font-bold text-sm tracking-wider">
                      {submittedData.accessCode}
                    </div>
                    <div className="text-slate-400 pt-1">
                      Doanh nghiệp: <span className="text-white">{formData.company}</span>
                    </div>
                    <div className="text-slate-400">
                      Email tiếp nhận: <span className="text-white">{submittedData.email}</span>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => setSubmittedData(null)}
                      className="px-6 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-all"
                    >
                      Đăng ký thêm tài khoản khác
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-1">
                    <h3 className="text-xl sm:text-2xl font-bold text-white">
                      Đăng Ký Trải Nghiệm COSA OS
                    </h3>
                    <p className="text-xs sm:text-sm text-slate-400">
                      Gói OPC hoàn toàn miễn phí cho giai đoạn phân tích dự án &amp; người dùng.
                    </p>
                  </div>

                  {errorMessage && (
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                      {errorMessage}
                    </div>
                  )}

                  {/* Full Name & Work Email */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                          className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Email công việc *
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="email"
                          required
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          placeholder="founder@company.vn"
                          className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Phone & Company */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                          className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Tên doanh nghiệp / Dự án *
                      </label>
                      <div className="relative">
                        <Building className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          required
                          value={formData.company}
                          onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                          placeholder="COSA AI JSC hoặc Dự án cá nhân"
                          className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Team Size & Priority */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Quy mô nhân sự
                      </label>
                      <select
                        value={formData.teamSize}
                        onChange={(e) => setFormData({ ...formData, teamSize: e.target.value })}
                        className="w-full px-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white transition-all"
                      >
                        <option value="1 (OPC)">1 nhân sự (OPC - Doanh nghiệp 1 người)</option>
                        <option value="2-5">2 - 5 nhân sự (Solo / Seed)</option>
                        <option value="5-20">5 - 20 nhân sự (Startup)</option>
                        <option value="20-50">20 - 50 nhân sự (Growth SME)</option>
                        <option value="50-200">50 - 200 nhân sự (Scaleup)</option>
                        <option value="200+">200+ nhân sự (Enterprise)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Nhu cầu ưu tiên
                      </label>
                      <select
                        value={formData.priorityInterest}
                        onChange={(e) => setFormData({ ...formData, priorityInterest: e.target.value })}
                        className="w-full px-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white transition-all"
                      >
                        <option value="OPC - Phân Tích Dự Án & Người Dùng (Free)">OPC - Phân Tích Dự Án &amp; Người Dùng (Miễn Phí)</option>
                        <option value="Trọn bộ Hệ điều hành COSA OS">Trọn bộ COSA OS</option>
                        <option value="Chiến Lược 12 Tuần & OKRs">Chiến Lược &amp; OKRs</option>
                        <option value="Unified Workforce (AI + Human)">Nhân sự AI + Người</option>
                        <option value="Kế Toán Thông tư 58/TT-BTC & Phê Duyệt Chi">Kế Toán Thông tư 58/TT-BTC</option>
                        <option value="Trợ Lý AI Đa Nhiệm">Trợ Lý AI Đa Nhiệm</option>
                        <option value="Bảo Mật On-Premise">Triển khai Máy chủ Riêng</option>
                      </select>
                    </div>
                  </div>

                  {/* Note */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Bài toán vận hành đang gặp phải (Tùy chọn)
                    </label>
                    <textarea
                      rows={2}
                      value={formData.note}
                      onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                      placeholder="Ví dụ: Cần tự động hóa theo dõi OKRs 12 tuần, kế toán Thông tư 58/TT-BTC..."
                      className="w-full px-3.5 py-2 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white placeholder-slate-600 transition-all resize-none"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-4 rounded-xl font-bold text-sm text-slate-950 bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue hover:from-white hover:to-cosa-cyan shadow-[0_0_30px_rgba(0,240,255,0.4)] transition-all flex items-center justify-center gap-2 transform active:scale-95 disabled:opacity-50"
                  >
                    {loading ? (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                        <span>Đang Cấp Mã VIP & Gửi Email Xác Nhận...</span>
                      </div>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 text-slate-950" />
                        <span>Xác Nhận Đăng Ký & Nhận Mã VIP Early Access</span>
                        <ArrowRight className="w-4 h-4 text-slate-950" />
                      </>
                    )}
                  </button>

                  <p className="text-[11px] text-center text-slate-500">
                    Bảo mật tuyệt đối thông tin. Email xác nhận gửi tự động qua Resend Cloud API.
                  </p>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
