"use client";

import React from "react";
import { motion } from "framer-motion";
import { Users, Bot, Target, FileSpreadsheet, Sparkles, Layers, ShieldCheck, Check } from "lucide-react";

export function IntroFeaturesMatrix() {
  const features = [
    {
      icon: Users,
      number: "01",
      title: "Nhân Lực Hợp Nhất & Mô Hình OPC",
      titleColor: "text-cyan-400",
      checkColor: "text-cyan-400",
      iconBg: "text-cyan-400 border-cyan-500/30",
      border: "border-cyan-500/30",
      glow: "group-hover:border-cyan-400 group-hover:shadow-[0_0_30px_rgba(0,240,255,0.2)]",
      checklist: [
        "1 Founder chỉ huy 6 Chuyên viên AI cốt lõi (Chiến lược, Tiếp thị, Bán hàng, Pháp lý...)",
        "3 cấp độ tự chủ thông minh: L0 Quan sát · L1 Đề xuất · L2 Thực thi",
        "Tối ưu hóa năng suất gấp 10 lần cho mô hình doanh nghiệp một người (OPC)",
      ],
    },
    {
      icon: Target,
      number: "02",
      title: "Chiến Lược 12 Tuần & Quản Trị OKRs",
      titleColor: "text-violet-400",
      checkColor: "text-violet-400",
      iconBg: "text-violet-400 border-violet-500/30",
      border: "border-violet-500/30",
      glow: "group-hover:border-violet-400 group-hover:shadow-[0_0_30px_rgba(139,92,246,0.2)]",
      checklist: [
        "Phân rã mục tiêu năm thành chu kỳ 12 tuần hành động tập trung",
        "Tự động đồng bộ thành các Sprint công việc hàng tuần cho đội ngũ",
        "Giám sát tiến độ và đo lường kết quả then chốt (OKRs) theo thời gian thực",
      ],
    },
    {
      icon: FileSpreadsheet,
      number: "03",
      title: "Dòng Tiền Chuẩn Thông Tư 58/TT-BTC",
      titleColor: "text-emerald-400",
      checkColor: "text-emerald-400",
      iconBg: "text-emerald-400 border-emerald-500/30",
      border: "border-emerald-500/30",
      glow: "group-hover:border-emerald-400 group-hover:shadow-[0_0_30px_rgba(16,185,129,0.2)]",
      checklist: [
        "Chuẩn hóa sổ sách thu chi theo Thông tư 58/TT-BTC",
        "Dự báo dòng tiền ròng & tự động cảnh báo nguy cơ thâm hụt",
        "Thiết lập chốt chặn phê duyệt chi tiêu tài chính tức thời",
      ],
    },
    {
      icon: Bot,
      number: "04",
      title: "Trợ Lý AI Điều Hành Đa Kênh",
      titleColor: "text-sky-400",
      checkColor: "text-sky-400",
      iconBg: "text-sky-400 border-sky-500/30",
      border: "border-sky-500/30",
      glow: "group-hover:border-sky-400 group-hover:shadow-[0_0_30px_rgba(56,189,248,0.2)]",
      checklist: [
        "Phản hồi siêu tốc <280ms, tương tác tự nhiên qua giọng nói",
        "Tích hợp kết nối trực tiếp trên Zalo, Telegram và WhatsApp",
        "Thực thi mệnh lệnh điều hành doanh nghiệp qua ngôn ngữ tự nhiên",
      ],
    },
    {
      icon: ShieldCheck,
      number: "05",
      title: "Lưu Trữ Riêng & Bảo Mật Tuyệt Đối",
      titleColor: "text-purple-400",
      checkColor: "text-purple-400",
      iconBg: "text-purple-400 border-purple-500/30",
      border: "border-purple-500/30",
      glow: "group-hover:border-purple-400 group-hover:shadow-[0_0_30px_rgba(168,85,247,0.2)]",
      checklist: [
        "Triển khai độc lập trên máy chủ riêng (VPS / On-Premise)",
        "Mã hóa định danh dữ liệu chuẩn Snowflake 64-bit ID",
        "Chính sách Zero Data Retention: bảo vệ 100% bí mật dữ liệu",
      ],
    },
    {
      icon: Sparkles,
      number: "06",
      title: "Miễn Phí 100% Phân Tích Dự Án",
      titleColor: "text-teal-300",
      checkColor: "text-teal-300",
      iconBg: "text-teal-300 border-teal-500/30",
      border: "border-teal-500/40",
      glow: "group-hover:border-teal-400 group-hover:shadow-[0_0_30px_rgba(45,212,191,0.25)]",
      checklist: [
        "100% Free: Khảo sát ý tưởng & xác thực tính khả thi của dự án",
        "Nghiên cứu sâu chân dung khách hàng mục tiêu (User Persona)",
        "Lập hồ sơ yêu cầu sản phẩm (PRD) chi tiết trước khi triển khai",
      ],
    },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto my-14 px-4 sm:px-6 lg:px-8">
      {/* Header section */}
      <div className="text-center max-w-5xl mx-auto mb-12 px-2">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-3">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>6 TRỤ CỘT ĐỘT PHÁ &amp; NỀN TẢNG AI AGENT</span>
        </div>
        <h2 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-extrabold text-white tracking-wider uppercase leading-tight font-sans">
          TRỤ CỘT ĐỘT PHÁ CỦA{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-400">
            HỆ ĐIỀU HÀNH COSA OS
          </span>
        </h2>
        <p className="mt-3 text-sm sm:text-base text-slate-300 leading-relaxed max-w-3xl mx-auto">
          Không chỉ là chatbot độc lập, COSA OS là hệ điều hành doanh nghiệp hoàn chỉnh kết nối liền mạch giữa Chiến lược, Nhân sự AI &amp; Người thật, Tài chính và Khách hàng cho mô hình OPC &amp; Startups.
        </p>
      </div>

      {/* Grid Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
        {features.map((feat, idx) => {
          const Icon = feat.icon;
          return (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.08, duration: 0.4 }}
              className="relative group"
            >
              <div
                className={`h-full rounded-2xl bg-gradient-to-b from-slate-900/90 via-slate-950/80 to-[#070c18] border ${feat.border} ${feat.glow} p-6 sm:p-7 backdrop-blur-xl transition-all duration-300 flex flex-col justify-start`}
              >
                {/* Top Bar: Icon + Number badge */}
                <div className="flex items-center justify-between mb-5">
                  <div className={`p-3 rounded-xl bg-slate-800/80 border ${feat.iconBg} group-hover:scale-110 transition-all duration-300 shadow-md`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-2xl font-mono font-extrabold text-slate-700 group-hover:text-cyan-500/50 transition-colors">
                    {feat.number}
                  </span>
                </div>

                {/* Card Title with Distinct Color */}
                <h3 className={`text-lg sm:text-xl font-bold ${feat.titleColor} mb-4 leading-snug tracking-tight font-sans`}>
                  {feat.title}
                </h3>

                {/* Checklist Description */}
                <ul className="space-y-2.5 mt-1">
                  {feat.checklist.map((item, cIdx) => (
                    <li key={cIdx} className="flex items-start gap-2.5 text-xs sm:text-sm text-slate-300 leading-relaxed">
                      <Check className={`w-4 h-4 ${feat.checkColor} shrink-0 mt-0.5`} />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
