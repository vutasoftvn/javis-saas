import React from "react";
import {
  Cpu,
  ShieldCheck,
  Sparkles,
  FileCheck
} from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[#04070e] border-t border-cosa-border/80 pt-16 pb-12 text-slate-400 relative overflow-hidden">
      {/* Subtle Glow in background */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-cosa-cyan/5 blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 pb-12 border-b border-slate-800/80">
          {/* Brand Info */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cosa-cyan to-cosa-blue p-[1px] shadow-[0_0_15px_rgba(0,240,255,0.3)]">
                <div className="w-full h-full bg-[#04070e] rounded-[11px] flex items-center justify-center">
                  <Cpu className="w-5 h-5 text-cosa-cyan" />
                </div>
              </div>
              <div className="flex flex-col">
                <span className="font-extrabold text-lg tracking-wider text-white">
                  COSA <span className="text-cosa-cyan">OS</span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  Create · Operate · Scale · Automate
                </span>
              </div>
            </div>
            <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
              Hệ điều hành doanh nghiệp AI thế hệ mới: Hợp nhất nhân sự Người thật & AI Agents trong một tổ chức, quản trị chu kỳ chiến lược 12 tuần, điều hành rảnh tay bằng Giọng nói Realtime và bảo mật dữ liệu On-Premise.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#0d172a] border border-cosa-border text-xs text-slate-300 font-mono">
                <ShieldCheck className="w-3.5 h-3.5 text-cosa-emerald" />
                <span>Zero Data Retention</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#0d172a] border border-cosa-border text-xs text-slate-300 font-mono">
                <FileCheck className="w-3.5 h-3.5 text-cosa-sky" />
                <span>Kế toán Thông tư 58/TT-BTC</span>
              </div>
            </div>
          </div>

          {/* Core Modules */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4 tracking-wide uppercase font-mono text-cosa-cyan">
              4 Cụm Nghiệp Vụ
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li><a href="#features" className="hover:text-white transition-colors">Unified Workforce (AI + Human)</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">Chiến Lược 12 Tuần & OKRs</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">Commercial & CRM B2B 360</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">Tài Chính Kế Toán & Dòng Tiền</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">AI Governance & Phê Duyệt Rủi Ro</a></li>
            </ul>
          </div>

          {/* AI Voice & Platform */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4 tracking-wide uppercase font-mono text-cosa-sky">
              Công Nghệ Nền Tảng
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li><a href="#ai-assistant" className="hover:text-white transition-colors">Trợ Lý AI Điều Hành (<span className="text-cosa-cyan">&lt;280ms</span>)</a></li>
              <li><a href="#architecture" className="hover:text-white transition-colors">Bảo Mật Local Data Plane Postgres</a></li>
              <li><a href="#architecture" className="hover:text-white transition-colors">Secure Vault & pgvector RAG</a></li>
              <li><a href="#architecture" className="hover:text-white transition-colors">Snowflake 64-bit ID B-Tree</a></li>
              <li><a href="#architecture" className="hover:text-white transition-colors">Triển Khai Máy Chủ Riêng (On-Premise)</a></li>
            </ul>
          </div>

          {/* Early Access & Contact */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4 tracking-wide uppercase font-mono text-cosa-emerald">
              Chương Trình Dùng Sớm
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li>
                <a href="#contact-form" className="text-cosa-cyan hover:underline flex items-center gap-1.5 font-medium">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Đăng ký Early Access VIP</span>
                </a>
              </li>
              <li><a href="#pricing" className="hover:text-white transition-colors">Chính sách ưu đãi 14 ngày</a></li>
              <li><a href="#roi-calculator" className="hover:text-white transition-colors">Dự toán ROI doanh nghiệp</a></li>
              <li><a href="#faq" className="hover:text-white transition-colors">Câu hỏi thường gặp</a></li>
              <li className="pt-2 text-xs text-slate-500 font-mono">
                Email gửi qua Resend Cloud API
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright & Disclaimer */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p>© {new Date().getFullYear()} COSA OS. Nền tảng điều hành doanh nghiệp AI tự trị hàng đầu Việt Nam.</p>
          <div className="flex items-center gap-6">
            <span className="text-slate-400">PostgreSQL Local + Supabase Central Architecture</span>
            <span className="text-cosa-cyan font-mono">v13.2 Stable</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
