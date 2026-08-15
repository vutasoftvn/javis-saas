import React from "react";
import { 
  Bot, 
  Mic, 
  Database, 
  Target, 
  Layers, 
  ShieldCheck, 
  Zap, 
  Cpu, 
  Workflow, 
  Server, 
  Sparkles,
  TrendingUp,
  Box,
  TerminalSquare
} from "lucide-react";

export const BentoFeatures: React.FC = () => {
  return (
    <section id="features" className="py-24 bg-[#04070e] relative overflow-hidden">
      {/* Background Neon Elements */}
      <div className="absolute top-1/3 right-0 w-[500px] h-[500px] bg-cosa-cyan/5 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-[400px] h-[400px] bg-cosa-blue/5 blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Title */}
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <Layers className="w-3.5 h-3.5" />
            <span>CORE ARCHITECTURAL PILLARS</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            5 Trụ Cột Đột Phá Của{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
              COSA OS Enterprise
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Không chỉ là một công cụ AI rời rạc, COSA OS là hệ điều hành toàn diện tích hợp sâu vào quy trình nghiệp vụ của doanh nghiệp.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-12 gap-6">
          {/* Card 1: AI Workforce (Large 8 cols) */}
          <div className="lg:col-span-8 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="absolute top-0 right-0 w-80 h-80 bg-cosa-cyan/10 rounded-bl-full blur-2xl pointer-events-none" />
            
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-cyan to-cosa-blue text-slate-950 font-bold shadow-[0_0_20px_rgba(0,240,255,0.4)]">
                <Bot className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-cyan tracking-wider">Trụ Cột 01</span>
                <h3 className="text-xl sm:text-2xl font-bold text-white">
                  Đội Ngũ AI Agent Tự Trị (AI Workforce)
                </h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm sm:text-base leading-relaxed mb-6">
              Thay vì sử dụng một chatbot đơn lẻ, COSA OS cung cấp <strong className="text-white">7 AI Agent chuyên trách</strong> đóng vai trò Giám đốc Chiến lược, Trưởng phòng Marketing, Chuyên viên Bán hàng, Kiến trúc sư Công nghệ, Luật sư Doanh nghiệp và Giám đốc Tài chính. Các Agent tự động giao tiếp và phản hồi chéo qua cơ chế LISTEN/NOTIFY Postgres.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 font-mono text-xs">
              {[
                { title: "CSO Iris", desc: "Hoạch định Chiến lược & OKRs", color: "text-cosa-cyan" },
                { title: "CMO Nova", desc: "Tăng trưởng & Nội dung", color: "text-cosa-sky" },
                { title: "VP Sales Rex", desc: "CRM & Chấm điểm Khách hàng", color: "text-cosa-emerald" },
                { title: "CTO Nexus", desc: "Kiến trúc & Sandbox Execution", color: "text-cosa-violet" },
                { title: "Legal Lex", desc: "Thẩm định Hợp đồng & Tuân thủ", color: "text-cosa-amber" },
                { title: "CFO Apex", desc: "Dự báo Dòng tiền & Chi phí", color: "text-rose-400" },
              ].map((ag, i) => (
                <div key={i} className="p-3 rounded-xl bg-[#0d172a] border border-cosa-border/80">
                  <div className={`font-bold ${ag.color}`}>{ag.title}</div>
                  <div className="text-[11px] text-slate-400 font-sans mt-0.5">{ag.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Card 2: Realtime Voice (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl flex flex-col justify-between">
            <div className="absolute bottom-0 right-0 w-60 h-60 bg-cosa-sky/10 rounded-tl-full blur-2xl pointer-events-none" />

            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-sky to-cosa-blue text-slate-950 font-bold shadow-[0_0_20px_rgba(56,189,248,0.4)]">
                  <Mic className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-xs font-mono uppercase text-cosa-sky tracking-wider">Trụ Cột 02</span>
                  <h3 className="text-xl font-bold text-white">Realtime Voice Agent</h3>
                </div>
              </div>

              <p className="text-slate-300 text-sm leading-relaxed mb-4">
                Tích hợp công nghệ <strong className="text-white">LiveKit Realtime</strong> cho phép điều khiển doanh nghiệp qua giọng nói 2 chiều với độ trễ siêu thấp dưới 300ms, hỗ trợ ngắt lời tự nhiên.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d172a] border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Audio Codec</span>
                <span className="text-cosa-cyan">Opus 48kHz HD</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Roundtrip Latency</span>
                <span className="text-cosa-emerald font-bold">&lt; 280ms</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Interruption</span>
                <span className="text-white">Full-Duplex VAD</span>
              </div>
            </div>
          </div>

          {/* Card 3: Enterprise Vault & Vector RAG (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-emerald to-teal-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(16,185,129,0.4)]">
                <Database className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-emerald tracking-wider">Trụ Cột 03</span>
                <h3 className="text-xl font-bold text-white">Enterprise Vault & RAG</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              Lưu trữ tài liệu bảo mật trên <strong className="text-white">MinIO S3</strong> kết hợp <strong className="text-white">PostgreSQL pgvector</strong>. Tối ưu độ chính xác trích xuất bằng <strong className="text-white">DSPy MIPROv2</strong>.
            </p>

            <ul className="space-y-2 text-xs text-slate-400 font-mono">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-emerald" />
                <span>Snowflake 64-bit ID B-Tree Indexing</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-emerald" />
                <span>Chunking & Embedding bất đồng bộ</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-emerald" />
                <span>Phân quyền Workspace & Brain cô lập</span>
              </li>
            </ul>
          </div>

          {/* Card 4: Autonomous Company Runtime (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-violet to-indigo-600 text-white font-bold shadow-[0_0_20px_rgba(139,92,246,0.4)]">
                <Target className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-violet tracking-wider">Trụ Cột 04</span>
                <h3 className="text-xl font-bold text-white">Company Runtime & OKRs</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              Quy trình khép kín từ <strong className="text-white">Tầm nhìn Chiến lược</strong> → <strong className="text-white">OKRs</strong> → <strong className="text-white">Phân rã Tasks</strong> → <strong className="text-white">Đo lường KPIs</strong>. Giúp toàn bộ doanh nghiệp luôn chạy đúng hướng mục tiêu.
            </p>

            <div className="p-3 rounded-xl bg-[#0d172a] border border-slate-800 text-xs text-slate-300 font-mono space-y-1">
              <div>🎯 1-Click Sync Strategy to Kanban</div>
              <div>⚡ Tự động cảnh báo điểm nghẽn tiến độ</div>
            </div>
          </div>

          {/* Card 5: Modular Landing & Hostinger CRM (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-amber to-orange-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(245,158,11,0.4)]">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-amber tracking-wider">Trụ Cột 05</span>
                <h3 className="text-xl font-bold text-white">Modular Landing & CRM</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              Không cần dùng landing builder thủ công. COSA tự sinh mã <strong className="text-white">Next.js module</strong>, tự deploy qua <strong className="text-white">Hostinger VPS MCP</strong> và thu thập Lead trực tiếp vào CRM Postgres.
            </p>

            <ul className="space-y-2 text-xs text-slate-400 font-mono">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-amber" />
                <span>Chấm điểm Lead ICP tự động</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-amber" />
                <span>Tích hợp Zalo OA, Resend, Webhook</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};
