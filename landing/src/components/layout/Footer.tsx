import React from "react";
import Link from "next/link";
import { 
  Cpu, 
  ShieldCheck, 
  Github, 
  Twitter, 
  Linkedin, 
  ExternalLink, 
  Terminal, 
  Zap,
  Lock,
  Server
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
              <span className="font-bold text-xl tracking-wider text-white">
                COSA<span className="text-cosa-cyan">.OS</span>
              </span>
            </div>
            <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
              Hệ điều hành doanh nghiệp tự trị đầu tiên tại Việt Nam kết hợp lực lượng lao động AI đa tác vụ, điều phối chiến lược OKRs, Realtime Voice và hạ tầng bảo mật On-Premise / Private Cloud.
            </p>
            <div className="flex items-center gap-3 pt-2">
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#0d172a] border border-cosa-border text-xs text-slate-300 font-mono">
                <ShieldCheck className="w-3.5 h-3.5 text-cosa-emerald" />
                <span>Zero Data Retention</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#0d172a] border border-cosa-border text-xs text-slate-300 font-mono">
                <Server className="w-3.5 h-3.5 text-cosa-sky" />
                <span>Snowflake 64-bit ID</span>
              </div>
            </div>
          </div>

          {/* Product Modules */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4 tracking-wide uppercase font-mono text-cosa-cyan">
              Sản Phẩm & Module
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li><a href="#ai-team" className="hover:text-white transition-colors">AI Workforce (7 Agents)</a></li>
              <li><a href="#voice-hub" className="hover:text-white transition-colors">LiveKit Realtime Voice</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">Strategy & OKR Engine</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">Enterprise Vault & RAG</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">OpenSandbox Execution</a></li>
              <li><a href="#features" className="hover:text-white transition-colors">Modular Landing & CRM</a></li>
            </ul>
          </div>

          {/* Solutions & Deploy */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4 tracking-wide uppercase font-mono text-cosa-sky">
              Giải Pháp & Triển Khai
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li><a href="#pricing" className="hover:text-white transition-colors">Dành cho Tech Founders</a></li>
              <li><a href="#pricing" className="hover:text-white transition-colors">Doanh Nghiệp SME & Scaleup</a></li>
              <li><a href="#architecture" className="hover:text-white transition-colors">Triển khai On-Premise</a></li>
              <li><a href="#architecture" className="hover:text-white transition-colors">Hostinger VPS 1-Click Deploy</a></li>
              <li><a href="#roi-calculator" className="hover:text-white transition-colors">Tính Toán Tối Ưu Chi Phí</a></li>
              <li><a href="#faq" className="hover:text-white transition-colors">Câu Hỏi Thường Gặp (FAQ)</a></li>
            </ul>
          </div>

          {/* Developers & Architecture */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4 tracking-wide uppercase font-mono text-cosa-emerald">
              Hạ Tầng & Công Nghệ
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li className="flex items-center gap-1.5"><Terminal className="w-3.5 h-3.5 text-cosa-cyan" /><span>FastAPI Brain API v13.2</span></li>
              <li className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-cosa-sky" /><span>PostgreSQL pgvector</span></li>
              <li className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-cosa-violet" /><span>DSPy Prompt Optimizer</span></li>
              <li className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-cosa-emerald" /><span>MinIO Private Object Vault</span></li>
              <li className="flex items-center gap-1.5"><Server className="w-3.5 h-3.5 text-cosa-amber" /><span>DeepSeek & OpenRouter</span></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span>© 2026 COSA OS. All rights reserved.</span>
            <span>•</span>
            <span className="text-slate-400 font-mono">Engineered for High-Velocity Autonomous Enterprises</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-slate-300 transition-colors">Chính Sách Bảo Mật</a>
            <a href="#" className="hover:text-slate-300 transition-colors">Điều Khoản Dịch Vụ</a>
            <a href="#" className="hover:text-slate-300 transition-colors">Cam Kết SLA 99.9%</a>
          </div>
        </div>
      </div>
    </footer>
  );
};
