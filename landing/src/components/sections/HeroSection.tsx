"use client";

import React, { useState, useEffect } from "react";
import { 
  Terminal, 
  Sparkles, 
  ArrowRight, 
  Play, 
  Shield, 
  Zap, 
  Cpu, 
  CheckCircle2, 
  Activity,
  Bot,
  Mic,
  Database,
  Radio
} from "lucide-react";

interface HeroSectionProps {
  onOpenLeadModal: (source?: string) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onOpenLeadModal }) => {
  const [activeTab, setActiveTab] = useState<"terminal" | "agents" | "voice">("terminal");
  const [typedTextIndex, setTypedTextIndex] = useState(0);

  const commandSteps = [
    { time: "00:01.02", tag: "BRAIN-API", text: "POST /api/v1/strategy/execute-plan -> Session #8941", color: "text-cosa-cyan" },
    { time: "00:01.24", tag: "WORKER-LISTEN", text: "NOTIFY received. Spawning Strategy & Tech Agent swarm...", color: "text-cosa-sky" },
    { time: "00:01.89", tag: "VAULT-RAG", text: "Retrieved 14 contextual embeddings from pgvector (cos_sim > 0.88)", color: "text-cosa-violet" },
    { time: "00:02.45", tag: "DSPY-OPTIMIZER", text: "Applying MIPROv2 prompt optimization with DeepSeek V3", color: "text-cosa-amber" },
    { time: "00:03.10", tag: "SANDBOX-EXEC", text: "Generated 3 OKRs, 12 Actionable Tasks, and CRM Landing micro-module", color: "text-cosa-emerald" },
  ];

  return (
    <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32 overflow-hidden bg-radial-vignette">
      {/* Background Cyberpunk Grid & Glow Orbs */}
      <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-glow opacity-60 blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 right-10 w-[400px] h-[400px] bg-blue-glow opacity-40 blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-4xl mx-auto space-y-6">
          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] lg:leading-[1.18] pb-2">
            Vận Hành Doanh Nghiệp Tự Trị Bằng{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue neon-text-glow inline-block pt-1">
              Đội Ngũ AI Đa Tác Vụ
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Hợp nhất toàn diện <strong className="text-white">Hoạch định Chiến lược OKRs</strong>, <strong className="text-white">Trợ lý Giọng nói Realtime LiveKit</strong>, <strong className="text-white">Kho Tri thức RAG pgvector</strong> và <strong className="text-white">Hệ thống CRM Tự Động Hóa</strong> trong một nền tảng duy nhất, bảo mật On-Premise.
          </p>

          {/* CTA Group */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={() => onOpenLeadModal("hero_primary_cta")}
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-bold text-base text-black bg-gradient-to-r from-cosa-cyan to-cosa-sky hover:from-white hover:to-cosa-cyan shadow-[0_0_30px_rgba(0,240,255,0.4)] hover:shadow-[0_0_45px_rgba(0,240,255,0.7)] transition-all flex items-center justify-center gap-2 transform active:scale-95"
            >
              <Sparkles className="w-5 h-5 text-slate-950" />
              <span>Khởi Chạy Bản Demo Miễn Phí</span>
              <ArrowRight className="w-5 h-5 text-slate-950" />
            </button>

            <a
              href="#playground"
              className="w-full sm:w-auto px-7 py-4 rounded-xl font-semibold text-base text-slate-200 bg-[#0d172a]/90 hover:bg-[#141c2e] border border-cosa-border hover:border-cosa-cyan/50 shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-cosa-cyan fill-cosa-cyan/20" />
              <span>Khám Phá Live Sandbox</span>
            </a>
          </div>

          {/* Metric Badges */}
          <div className="pt-6 grid grid-cols-2 md:grid-cols-4 gap-3 max-w-3xl mx-auto">
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-cyan font-mono">10x</div>
              <div className="text-xs text-slate-400">Tốc độ ra quyết định</div>
            </div>
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-emerald font-mono">99.8%</div>
              <div className="text-xs text-slate-400">Độ chính xác RAG Tri thức</div>
            </div>
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-sky font-mono">0-Leak</div>
              <div className="text-xs text-slate-400">Bảo mật On-Premise</div>
            </div>
            <div className="p-3 rounded-xl bg-[#0d172a]/60 border border-cosa-border/60 backdrop-blur-md">
              <div className="text-2xl font-bold text-cosa-violet font-mono">-70%</div>
              <div className="text-xs text-slate-400">Chi phí vận hành nhân sự</div>
            </div>
          </div>
        </div>

        {/* Interactive Holographic Command Console Preview */}
        <div className="mt-14 max-w-5xl mx-auto">
          <div className="relative rounded-2xl bg-[#080f1e]/90 border border-cosa-cyan/30 shadow-[0_0_60px_-15px_rgba(0,240,255,0.25)] backdrop-blur-2xl overflow-hidden">
            {/* Top Window Chrome */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#04070e] border-b border-cosa-border">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="ml-2 text-xs font-mono text-slate-400 hidden sm:inline-block">
                  cosa-brain@autonomous-cluster:~# session --stream
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
                  <span>Agent Stream</span>
                </button>
                <button
                  onClick={() => setActiveTab("agents")}
                  className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all flex items-center gap-1.5 ${
                    activeTab === "agents"
                      ? "bg-cosa-cyan/20 text-cosa-cyan border border-cosa-cyan/40"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Bot className="w-3.5 h-3.5" />
                  <span>AI Swarm (7)</span>
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
                  <span>Voice Hologram</span>
                </button>
              </div>
            </div>

            {/* Console Body Content */}
            <div className="p-6 font-mono text-xs sm:text-sm min-h-[300px] flex flex-col justify-between">
              {activeTab === "terminal" && (
                <div className="space-y-3.5">
                  <div className="text-slate-500 font-mono text-xs pb-1 border-b border-slate-800 flex items-center justify-between">
                    <span>STATUS: EXECUTING MULTI-AGENT PIPELINE</span>
                    <span className="text-cosa-cyan">LATENCY: 42ms | SNOWFLAKE: 8492049182390184</span>
                  </div>
                  {commandSteps.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-3 animate-fadeIn">
                      <span className="text-slate-500 shrink-0">[{step.time}]</span>
                      <span className={`px-1.5 py-0.2 rounded bg-slate-800/80 shrink-0 font-semibold text-[11px] ${step.color}`}>
                        {step.tag}
                      </span>
                      <span className="text-slate-200">{step.text}</span>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 pt-2 text-cosa-cyan animate-pulse">
                    <span>❯</span>
                    <span>AI agents ready for next instruction...</span>
                    <span className="w-2 h-4 bg-cosa-cyan inline-block animate-ping" />
                  </div>
                </div>
              )}

              {activeTab === "agents" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {[
                    { role: "Chief Strategy Officer", name: "CSO Iris", model: "DeepSeek V3", status: "Active Roadmapping", color: "border-cosa-cyan text-cosa-cyan" },
                    { role: "Marketing Growth Lead", name: "CMO Nova", model: "Claude 3.5 Sonnet", status: "Auto-Ad & Landing Gen", color: "border-cosa-sky text-cosa-sky" },
                    { role: "Enterprise Sales AE", name: "VP Sales Rex", model: "GPT-4o", status: "Lead Scoring Pipeline", color: "border-cosa-emerald text-cosa-emerald" },
                    { role: "Lead Solutions Architect", name: "CTO Nexus", model: "Claude 3.7", status: "Sandbox Code Execution", color: "border-cosa-violet text-cosa-violet" },
                    { role: "Corporate Legal Counsel", name: "Legal Lex", model: "DeepSeek R1", status: "Contract Compliance", color: "border-cosa-amber text-cosa-amber" },
                    { role: "Chief Financial Officer", name: "CFO Apex", model: "GPT-4o", status: "Cashflow & Burn Forecast", color: "border-rose-400 text-rose-400" },
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
                    <h4 className="text-white font-bold text-base">LiveKit Realtime Voice Agent Hub</h4>
                    <p className="text-xs text-slate-400 max-w-md">
                      Hội thoại giọng nói thời gian thực không độ trễ. Điều khiển toàn bộ hoạt động công ty qua khẩu lệnh tự nhiên.
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
                  <span>Worker State: Event-driven Listen/Notify Postgres</span>
                </div>
                <div className="flex items-center gap-4">
                  <span>FastAPI + MinIO Vault</span>
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
