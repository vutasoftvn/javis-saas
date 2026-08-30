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

              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-border">
                <div className="p-2 rounded-xl bg-cosa-violet/10 text-cosa-violet shrink-0">
                  <BadgeCheck className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Miễn Phí 14 Ngày Trọn Gói</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Kích hoạt đầy đủ 6 Chuyên viên AI, Trợ lý Giọng nói LiveKit và sổ sách kế toán chuẩn Thông tư 88.
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
                  <div className="w-16 h-16 rounded-full bg-cosa-emerald/20 border border-cosa-emerald text-cosa-emerald mx-auto flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.4)]">
                    <CheckCircle2 className="w-9 h-9" />
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-2xl font-bold text-white">Đăng Ký Early Access Thành Công!</h3>
                    <p className="text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
                      Email xác nhận đã được chuyển qua Resend tới hộp thư: <strong className="text-cosa-cyan">{submittedData.email}</strong>.
                    </p>
                  </div>

                  {/* VIP Pass Card */}
                  <div className="p-5 rounded-2xl bg-[#04070e] border border-cosa-cyan/40 max-w-md mx-auto text-left space-y-2 shadow-xl">
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                      <span>MÃ THẺ VIP DÙNG SỚM</span>
                      <span className="text-emerald-400 font-semibold">ĐÃ KÍCH HOẠT</span>
                    </div>
                    <div className="text-2xl sm:text-3xl font-extrabold text-cosa-cyan tracking-wider font-mono">
                      {submittedData.accessCode}
                    </div>
                    <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                      Đội ngũ sáng lập COSA OS sẽ liên hệ trong vòng <strong>2-4 giờ làm việc</strong> để sắp xếp buổi demo riêng.
                    </div>
                  </div>

                  <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                    <button
                      onClick={() => setSubmittedData(null)}
                      className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[#0d172a] text-slate-300 hover:text-white border border-slate-700 text-xs font-mono transition-colors"
                    >
                      Đăng Ký Doanh Nghiệp Khác
                    </button>
                    <a
                      href="mailto:support@cosa.os"
                      className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-cosa-cyan to-cosa-sky text-slate-950 text-xs font-bold font-mono"
                    >
                      Hỗ Trợ Nhanh 24/7
                    </a>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="pb-3 border-b border-slate-800 flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-white">Đăng Ký Quyền Sử Dụng Sớm (Waitlist VIP)</h3>
                      <p className="text-xs text-slate-400 mt-0.5">Nhận tài khoản thử nghiệm 14 ngày & vé demo 1-on-1.</p>
                    </div>
                    <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#0d172a] border border-cosa-cyan/40 text-[11px] font-mono text-cosa-cyan">
                      <Clock className="w-3 h-3" />
                      <span>Còn 42 Suất</span>
                    </div>
                  </div>

                  {errorMessage && (
                    <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Full Name */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Họ và tên <span className="text-rose-400">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <User className="w-4 h-4" />
                        </div>
                        <input
                          type="text"
                          required
                          value={formData.fullName}
                          onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                          placeholder="Nguyễn Văn A"
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan focus:ring-1 focus:ring-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>

                    {/* Email */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Email Doanh nghiệp <span className="text-rose-400">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <Mail className="w-4 h-4" />
                        </div>
                        <input
                          type="email"
                          required
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          placeholder="founder@company.com"
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan focus:ring-1 focus:ring-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Phone / Zalo */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Số điện thoại / Zalo <span className="text-rose-400">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <Phone className="w-4 h-4" />
                        </div>
                        <input
                          type="tel"
                          required
                          value={formData.phone}
                          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                          placeholder="0912 345 678"
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan focus:ring-1 focus:ring-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>

                    {/* Company */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Tên Công ty / Startup <span className="text-rose-400">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <Building className="w-4 h-4" />
                        </div>
                        <input
                          type="text"
                          required
                          value={formData.company}
                          onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                          placeholder="Acme Corp"
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan focus:ring-1 focus:ring-cosa-cyan text-sm text-white placeholder-slate-600 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Role */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Chức vụ của bạn
                      </label>
                      <select
                        value={formData.role}
                        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                        className="w-full px-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white transition-all"
                      >
                        <option value="Founder / CEO">Founder / CEO</option>
                        <option value="COO / Giám Đốc Vận Hành">COO / Vận Hành</option>
                        <option value="CTO / Trưởng Nhóm Tech">CTO / Kỹ Thuật</option>
                        <option value="CFO / Kế Toán Trưởng">CFO / Kế Toán</option>
                        <option value="Trưởng Phòng Kinh Doanh">Kinh Doanh / Sales</option>
                        <option value="Khác">Vai trò khác</option>
                      </select>
                    </div>

                    {/* Team Size */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Quy mô nhân sự
                      </label>
                      <select
                        value={formData.teamSize}
                        onChange={(e) => setFormData({ ...formData, teamSize: e.target.value })}
                        className="w-full px-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white transition-all"
                      >
                        <option value="1-5">1 - 5 nhân sự (Solo / Seed)</option>
                        <option value="5-20">5 - 20 nhân sự (Startup)</option>
                        <option value="20-50">20 - 50 nhân sự (Growth SME)</option>
                        <option value="50-200">50 - 200 nhân sự (Scaleup)</option>
                        <option value="200+">200+ nhân sự (Enterprise)</option>
                      </select>
                    </div>

                    {/* Priority Interest */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Nhu cầu ưu tiên
                      </label>
                      <select
                        value={formData.priorityInterest}
                        onChange={(e) => setFormData({ ...formData, priorityInterest: e.target.value })}
                        className="w-full px-3 py-2.5 rounded-xl bg-[#04070e] border border-cosa-border focus:border-cosa-cyan text-sm text-white transition-all"
                      >
                        <option value="Trọn bộ Hệ điều hành COSA OS">Trọn bộ COSA OS</option>
                        <option value="Chiến Lược 12 Tuần & OKRs">Chiến Lược & OKRs</option>
                        <option value="Unified Workforce (AI + Human)">Nhân sự AI + Người</option>
                        <option value="Kế Toán TT88 & Phê Duyệt Chi">Kế Toán TT88 & Dòng Tiền</option>
                        <option value="LiveKit Realtime Voice">Trợ lý Giọng nói LiveKit</option>
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
                      placeholder="Ví dụ: Cần tự động hóa theo dõi OKRs 12 tuần, thiếu nhân sự kế toán TT88..."
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
