"use client";

import React, { useState } from "react";
import {
  Terminal,
  Sparkles,
  ArrowRight,
  Play,
  Activity,
  Mic,
  Radio,
  Users,
} from "lucide-react";

interface HeroSectionProps {
  onOpenLeadModal: (source?: string) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onOpenLeadModal }) => {
  const [activeTab, setActiveTab] = useState<"terminal" | "agents" | "voice">("terminal");

  const commandSteps = [
    { time: "00:01.02", tag: "STRATEGY-SYNC", text: "Khởi động Chu kỳ 12 Tuần: Phân rã 4 Objectives & 12 Key Results cấp công ty", color: "text-cosa-cyan" },
    { time: "00:01.35", tag: "WORKFORCE-DISPATCH", text: "Phân bổ 18 Tasks tự động cho Nhân sự Thực + Chuyên viên AI (L1/L2 Autonomy)", color: "text-cosa-sky" },
    { time: "00:01.88", tag: "FINANCE-TT88", text: "Đồng bộ sổ cái thu chi TT88: Dự báo dòng tiền ròng Q3 thặng dư 1.48 tỷ VNĐ", color: "text-cosa-emerald" },
    { time: "00:02.40", tag: "GOVERNANCE-GATE", text: "Hành động chi ngân sách quảng cáo > 20M: Yêu cầu Founder phê duyệt (REQUIRE_APPROVAL)", color: "text-cosa-amber" },
    { time: "00:03.12", tag: "LIVEKIT-VOICE", text: "Hologram Voice Agent sẵn sàng: Điều khiển toàn bộ dashboard bằng khẩu lệnh tiếng Việt", color: "text-cosa-violet" },
  ];

  return (
    <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32 overflow-hidden bg-radial-vignette">
      {/* Background Cyberpunk Grid & Glow Orbs */}
      <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-glow opacity-60 blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 right-10 w-[400px] h-[400px] bg-blue-glow opacity-40 blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-4xl mx-auto space-y-6">
          {/* Top Pill */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#0d172a]/90 border border-cosa-cyan/40 text-cosa-cyan text-xs font-mono backdrop-blur-md shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            <span>COSA OS · HỆ ĐIỀU HÀNH DOANH NGHIỆP AI TỰ TRỊ</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] lg:leading-[1.18] pb-2">
            Vận Hành Doanh Nghiệp Tự Trị Cho{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue neon-text-glow inline-block pt-1">
              Nhà Sáng Lập Hiện Đại
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Hợp nhất <strong className="text-white">Lực lượng Lao động AI & Người thật</strong> trong một sơ đồ tổ chức duy nhất. Vận hành chu kỳ chiến lược <strong className="text-white">12-Week Year & OKRs</strong>, quản trị dòng tiền <strong className="text-white">Kế toán TT88/TT58</strong> và điều khiển rảnh tay bằng <strong className="text-white">Giọng nói Realtime LiveKit</strong>.
          </p>

          {/* CTA Group */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={() => onOpenLeadModal("hero_primary_cta")}
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-bold text-base text-slate-950 bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue hover:from-white hover:to-cosa-cyan shadow-[0_0_30px_rgba(0,240,255,0.4)] hover:shadow-[0_0_45px_rgba(0,240,255,0.7)] transition-all flex items-center justify-center gap-2 transform active:scale-95"
            >
              <Sparkles className="w-5 h-5 text-slate-950" />
              <span>Đăng Ký Quyền Sử Dụng Sớm</span>
              <ArrowRight className="w-5 h-5 text-slate-950" />
            </button>

            <a
              href="#features"
              className="w-full sm:w-auto px-7 py-4 rounded-xl font-semibold text-base text-slate-200 bg-[#0d172a]/90 hover:bg-[#141c2e] border border-cosa-border hover:border-cosa-cyan/50 shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-cosa-cyan fill-cosa-cyan/20" />
              <span>Khám Phá 4 Cụm Nghiệp Vụ</span>
            </a>
          </div>

          {/* Metric Badges */}
          <div className="pt-6 grid grid-cols-2 md:grid-cols-4 gap-3 max-w-3xl mx-auto">
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-cyan font-mono">10x</div>
              <div className="text-xs text-slate-400">Tốc độ thực thi OKRs</div>
            </div>
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-emerald font-mono">1 Sơ Đồ</div>
              <div className="text-xs text-slate-400">Hợp nhất AI + Người thật</div>
            </div>
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-sky font-mono">&lt; 300ms</div>
              <div className="text-xs text-slate-400">Độ trễ Voice LiveKit</div>
            </div>
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-violet font-mono">100%</div>
              <div className="text-xs text-slate-400">Chủ quyền On-Premise</div>
            </div>
          </div>
        </div>

        {/* Interactive Command Console Preview */}
        <div className="mt-14 max-w-5xl mx-auto">
          <div className="relative rounded-2xl bg-[#080f1e]/90 border border-cosa-cyan/30 shadow-[0_0_60px_-15px_rgba(0,240,255,0.25)] backdrop-blur-2xl overflow-hidden">
            {/* Top Window Chrome */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#04070e] border-b border-cosa-border">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="ml-2 text-xs font-mono text-slate-400 hidden sm:inline-block">
                  cosa-control-plane@enterprise-node:4000 (~/operations)
                </span>
              </div>

              {/* Tab Selector */}
              <div className="flex items-center gap-1 bg-[#0d172a] p-1 rounded-lg border border-cosa-border">
                <button
                  onClick={() => setActiveTab("terminal")}
                  className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all flex items-center gap-1.5 ${
                    activeTab === "terminal"
                      ? "bg-cosa-cyan/20 text-cosa-cyan border border-cosa-cyan/40"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Terminal className="w-3.5 h-3.5" />
                  <span>Operations Stream</span>
                </button>
                <button
                  onClick={() => setActiveTab("agents")}
                  className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all flex items-center gap-1.5 ${
                    activeTab === "agents"
                      ? "bg-cosa-cyan/20 text-cosa-cyan border border-cosa-cyan/40"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Users className="w-3.5 h-3.5" />
                  <span>AI Workforce (6)</span>
                </button>
                <button
                  onClick={() => setActiveTab("voice")}
                  className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all flex items-center gap-1.5 ${
                    activeTab === "voice"
                      ? "bg-cosa-cyan/20 text-cosa-cyan border border-cosa-cyan/40"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Radio className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
                  <span>LiveKit Voice</span>
                </button>
              </div>
            </div>

            {/* Console Body Content */}
            <div className="p-6 font-mono text-xs sm:text-sm min-h-[300px] flex flex-col justify-between">
              {activeTab === "terminal" && (
                <div className="space-y-3.5">
                  <div className="text-slate-500 font-mono text-xs pb-1 border-b border-slate-800 flex items-center justify-between">
                    <span>HỆ ĐIỀU HÀNH DOANH NGHIỆP TỰ TRỊ COSA OS · ENCORE.TS RUNTIME</span>
                    <span className="text-cosa-cyan">LOCAL DATA PLANE: POSTGRESQL (PORT 5433)</span>
                  </div>
                  {commandSteps.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-3 animate-fadeIn">
                      <span className="text-slate-500 shrink-0">[{step.time}]</span>
                      <span className={`px-1.5 py-0.5 rounded bg-slate-800/80 shrink-0 font-semibold text-[11px] ${step.color}`}>
                        {step.tag}
                      </span>
                      <span className="text-slate-200">{step.text}</span>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 pt-2 text-cosa-cyan animate-pulse">
                    <span>❯</span>
                    <span>Toàn bộ 4 cụm nghiệp vụ đang vận hành ổn định. Chờ khẩu lệnh tiếp theo...</span>
                    <span className="w-2 h-4 bg-cosa-cyan inline-block animate-ping" />
                  </div>
                </div>
              )}

              {activeTab === "agents" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {[
                    { role: "Chiến Lược & OKRs 12 Tuần", name: "CSO Iris", model: "DeepSeek R1", status: "L0 · Giám Sát Tiến Độ", color: "border-cosa-cyan text-cosa-cyan" },
                    { role: "Tăng Trưởng & Bối Cảnh Marketing", name: "CMO Nova", model: "DeepSeek V3", status: "L0 · Chiến Dịch Nội Dung", color: "border-cosa-sky text-cosa-sky" },
                    { role: "B2B Sales Pipeline & CRM", name: "VP Sales Rex", model: "DeepSeek V3", status: "L1 · Chấm Điểm ICP", color: "border-cosa-emerald text-cosa-emerald" },
                    { role: "Kiến Trúc & Phân Bổ Tasks", name: "CTO Nexus", model: "Claude 3.7", status: "L1 · Phân Rã Engineering", color: "border-cosa-violet text-cosa-violet" },
                    { role: "Thẩm Định Hợp Đồng & Tuân Thủ", name: "Legal Lex", model: "DeepSeek R1", status: "L0 · Audit Pháp Lý", color: "border-cosa-amber text-cosa-amber" },
                    { role: "Sổ Cái Kế Toán TT88 & Dòng Tiền", name: "CFO Apex", model: "DeepSeek V3", status: "L1 · Đề Xuất (Cần Duyệt Chi)", color: "border-rose-400 text-rose-400" },
                  ].map((ag, i) => (
                    <div key={i} className="p-3 rounded-xl bg-[#0d172a]/90 border border-cosa-border hover:border-cosa-cyan/40 transition-all">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-white">{ag.name}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">ONLINE</span>
                      </div>
                      <div className="text-[11px] text-slate-400">{ag.role}</div>
                      <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                        <span className="text-slate-500">{ag.model}</span>
                        <span className={ag.color}>{ag.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "voice" && (
                <div className="flex flex-col items-center justify-center py-6 text-center space-y-4">
                  <div className="relative flex items-center justify-center">
                    <div className="absolute w-28 h-28 rounded-full bg-cosa-cyan/20 animate-ping" />
                    <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-cosa-cyan to-cosa-blue flex items-center justify-center shadow-[0_0_30px_rgba(0,240,255,0.6)]">
                      <Mic className="w-9 h-9 text-slate-950" />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-white font-bold text-base">Hologram Voice Agent Hub (LiveKit Full-Duplex)</h4>
                    <p className="text-xs text-slate-400 max-w-md">
                      Hội thoại giọng nói thời gian thực &lt;300ms. Điều khiển toàn bộ bảng Kanban, duyệt chi ngân sách và tra cứu dữ liệu khách hàng bằng giọng nói tự nhiên.
                    </p>
                  </div>
                  {/* Waveform visualizer */}
                  <div className="flex items-center justify-center gap-1.5 h-8">
                    {[40, 75, 100, 60, 30, 85, 95, 45, 70, 100, 80, 50, 65, 90, 40].map((h, i) => (
                      <div
                        key={i}
                        className="w-1 bg-gradient-to-t from-cosa-cyan to-cosa-sky rounded-full animate-pulse"
                        style={{ height: `${h}%`, animationDelay: `${i * 0.08}s` }}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Bottom Quick Summary Bar */}
              <div className="mt-4 pt-3 border-t border-cosa-border/80 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Encore Microservices: Identity · Operations · Commercial · Finance-Legal</span>
                </div>
                <div className="flex items-center gap-4">
                  <span>Flutter Desktop App</span>
                  <span className="text-cosa-cyan">pgvector Indexed</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
