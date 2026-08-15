"use client";

import React, { useState } from "react";
import { 
  Play, 
  Sparkles, 
  CheckCircle2, 
  Terminal, 
  Bot, 
  Target, 
  Layers, 
  FileText, 
  Code2, 
  Cpu, 
  Zap,
  ArrowRight,
  TrendingUp
} from "lucide-react";

interface Scenario {
  id: string;
  title: string;
  category: string;
  icon: any;
  agentsInvolved: string[];
  prompt: string;
  executionSteps: {
    agent: string;
    role: string;
    action: string;
    output: string;
    status: string;
  }[];
  deliverables: {
    title: string;
    type: string;
    preview: string;
  };
}

interface LivePlaygroundProps {
  onOpenLeadModal: (source?: string) => void;
}

export const LivePlayground: React.FC<LivePlaygroundProps> = ({ onOpenLeadModal }) => {
  const scenarios: Scenario[] = [
    {
      id: "strategy-okrs",
      title: "Lập Chiến Lược Tăng Trưởng & Phân Rã OKRs",
      category: "Chiến Lược & Điều Hành",
      icon: Target,
      agentsInvolved: ["CSO Iris", "VP Sales Rex", "CTO Nexus"],
      prompt: "Mục tiêu: Đạt 100K USD MRR trong Q3 với sản phẩm AI SaaS B2B tại thị trường Đông Nam Á.",
      executionSteps: [
        {
          agent: "CSO Iris",
          role: "Chief Strategy Officer",
          action: "Phân tích 5 đối thủ cạnh tranh & Trích xuất insight từ Enterprise Vault",
          output: "Xác định 3 thị trường ngách có CAC thấp nhất và xây dựng Strategic Roadmap v3.",
          status: "Hoàn thành trong 1.2s",
        },
        {
          agent: "VP Sales Rex",
          role: "VP Enterprise Sales",
          action: "Thiết lập phễu bán hàng B2B & Chấm điểm Lead ICP tự động",
          output: "Định hình 4 giai đoạn Pipeline CRM và kịch bản tiếp cận 500 khách hàng Enterprise tiềm năng.",
          status: "Hoàn thành trong 0.9s",
        },
        {
          agent: "CTO Nexus",
          role: "Solutions Architect",
          action: "Phân rã 12 Engineering Tasks & Cấu hình OpenSandbox",
          output: "Liên kết trực tiếp OKRs với Kanban Board và gán deadline tự động.",
          status: "Hoàn thành trong 1.5s",
        },
      ],
      deliverables: {
        title: "Kế Hoạch Thực Thi Q3 Hoàn Chỉnh",
        type: "Strategic Matrix & OKR Tree",
        preview: "Objective 1: Tăng trưởng 150% Net New ARR\n  ├─ KR1: 50 Khách hàng Enterprise dùng thử\n  ├─ KR2: Tỷ lệ chốt hợp đồng Demo đạt 38%\n  └─ KR3: Thời gian triển khai < 48 giờ",
      },
    },
    {
      id: "marketing-landing",
      title: "Tự Động Sinh Landing Page & Tạo Phễu CRM",
      category: "Marketing & Tăng Trưởng",
      icon: TrendingUp,
      agentsInvolved: ["CMO Nova", "CTO Nexus", "VP Sales Rex"],
      prompt: "Tạo chiến dịch ra mắt tính năng AI Voice Assistant, sinh Landing Page Next.js và nối vào CRM Hostinger.",
      executionSteps: [
        {
          agent: "CMO Nova",
          role: "Growth & Content Lead",
          action: "Soạn thảo Copywriting AIDA & Định vị Value Proposition",
          output: "Hoàn thiện 8 Section nội dung tối ưu chuyển đổi và thông điệp truyền thông mạng xã hội.",
          status: "Hoàn thành trong 1.4s",
        },
        {
          agent: "CTO Nexus",
          role: "Solutions Architect",
          action: "Tự động sinh mã nguồn Next.js 15 App Router & Tailwind CSS",
          output: "Sinh cấu trúc component modular, tích hợp Form Submit API kết nối Postgres CRM.",
          status: "Hoàn thành trong 2.1s",
        },
        {
          agent: "VP Sales Rex",
          role: "VP Enterprise Sales",
          action: "Thiết lập luồng tự động gửi Email xác nhận & Chấm điểm Lead",
          output: "Kích hoạt Webhook CRM và phân bổ tư vấn viên theo ngành nghề.",
          status: "Hoàn thành trong 0.8s",
        },
      ],
      deliverables: {
        title: "Trang Đích (Landing Page) & Phễu Chuyển Đổi",
        type: "Generated Modular Next.js Artifact",
        preview: "✓ URL: https://demo.cosa-os.vn/campaign/voice-launch\n✓ Tích hợp Lead API: POST /api/v1/marketing/public/forms/submit\n✓ Tự động deploy: Hostinger VPS MCP (Docker Compose ready)",
      },
    },
    {
      id: "legal-audit",
      title: "Thẩm Định Hợp Đồng & Rủi Ro Pháp Lý",
      category: "Pháp Lý & Tuân Thủ",
      icon: FileText,
      agentsInvolved: ["Legal Lex", "CFO Apex"],
      prompt: "Thẩm định hợp đồng cung cấp dịch vụ công nghệ trị giá 500,000 USD với điều khoản SLA và bồi thường thiệt hại.",
      executionSteps: [
        {
          agent: "Legal Lex",
          role: "Corporate Counsel",
          action: "So sánh điều khoản hợp đồng với tiêu chuẩn luật thương mại & Vault Knowledge",
          output: "Phát hiện 2 điều khoản bất lợi về bồi hoàn vô giới hạn tại mục 8.4 và đề xuất bản sửa đổi.",
          status: "Hoàn thành trong 1.8s",
        },
        {
          agent: "CFO Apex",
          role: "Chief Financial Officer",
          action: "Đánh giá tác động dòng tiền và rủi ro phạt hợp đồng",
          output: "Đề xuất mức trần trách nhiệm pháp lý tối đa 100% giá trị hợp đồng.",
          status: "Hoàn thành trong 0.9s",
        },
      ],
      deliverables: {
        title: "Báo Cáo Thẩm Định & Đề Xuất Sửa Đổi Pháp Lý",
        type: "Redline Audit Document",
        preview: "⚠️ Điều khoản 8.4: Rủi ro Cao -> Đề xuất bổ sung điều khoản giới hạn trách nhiệm (Cap at 100% Contract Value).\n✓ Điều khoản 12.1: Bảo mật thông tin đạt chuẩn ISO/IEC 27001.",
      },
    },
  ];

  const [activeScenario, setActiveScenario] = useState<Scenario>(scenarios[0]);

  return (
    <section id="playground" className="py-24 bg-[#070c18] relative overflow-hidden">
      {/* Glow Backdrop */}
      <div className="absolute top-1/2 left-0 w-96 h-96 bg-cosa-cyan/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-cosa-blue/10 blur-[130px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            <span>LIVE INTERACTIVE PLAYGROUND</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Trải Nghiệm Trực Quan Cách{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan to-cosa-sky inline-block pt-1">
              COSA OS Xử Lý Thực Tế
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Chọn một kịch bản kinh doanh cụ thể để xem các AI Agent tự động phối hợp, truy xuất kho tri thức Vault và thực thi trong vài giây.
          </p>
        </div>

        {/* Scenario Selector Tabs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {scenarios.map((sc) => {
            const Icon = sc.icon;
            const isSelected = activeScenario.id === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => setActiveScenario(sc)}
                className={`p-5 rounded-2xl text-left transition-all relative overflow-hidden ${
                  isSelected
                    ? "bg-[#0d172a] border-2 border-cosa-cyan shadow-[0_0_25px_rgba(0,240,255,0.25)]"
                    : "bg-[#080f1e]/80 border border-cosa-border hover:border-slate-700 hover:bg-[#0d172a]/60"
                }`}
              >
                {isSelected && (
                  <div className="absolute top-0 right-0 w-16 h-16 bg-cosa-cyan/10 rounded-bl-full pointer-events-none" />
                )}
                <div className="flex items-center gap-3 mb-2">
                  <div className={`p-2.5 rounded-xl ${isSelected ? "bg-cosa-cyan text-black" : "bg-slate-800 text-slate-300"}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[11px] font-mono uppercase tracking-wider text-cosa-cyan">
                      {sc.category}
                    </span>
                    <h3 className="font-bold text-sm sm:text-base text-white line-clamp-1">
                      {sc.title}
                    </h3>
                  </div>
                </div>
                <p className="text-xs text-slate-400 mt-2 line-clamp-2">
                  {sc.prompt}
                </p>
              </button>
            );
          })}
        </div>

        {/* Interactive Execution Viewport */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-[#080f1e]/90 border border-cosa-border rounded-3xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
          {/* Left Column: Multi-Agent Workflow Logs */}
          <div className="lg:col-span-7 space-y-6">
            <div>
              <div className="text-xs font-mono text-slate-500 uppercase mb-2 flex items-center justify-between">
                <span>Prompt / Yêu Cầu Đầu Vào</span>
                <span className="text-cosa-cyan font-semibold">Tự Động Phân Phối AI Swarm</span>
              </div>
              <div className="p-4 rounded-xl bg-[#04070e] border border-cosa-border font-mono text-xs sm:text-sm text-slate-200">
                <span className="text-cosa-cyan">user@cosa-workspace:~$ </span>
                {activeScenario.prompt}
              </div>
            </div>

            {/* Steps stream */}
            <div className="space-y-4">
              <div className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cosa-cyan" />
                <span>Tiến Trình Phối Hợp Thực Thi Của Các AI Agent:</span>
              </div>

              {activeScenario.executionSteps.map((step, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[#0d172a]/90 border border-cosa-border/80 hover:border-cosa-cyan/30 transition-all space-y-2 relative"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-cosa-cyan animate-ping" />
                      <span className="font-bold text-sm text-white">{step.agent}</span>
                      <span className="text-xs text-slate-400">({step.role})</span>
                    </div>
                    <span className="text-[11px] font-mono text-cosa-emerald px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                      {step.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 font-medium">
                    🎯 <span className="text-slate-400">Hành động:</span> {step.action}
                  </div>
                  <div className="text-xs text-cosa-sky/90 bg-[#04070e]/60 p-2.5 rounded-lg border border-slate-800">
                    💡 <span className="text-slate-300">Kết quả:</span> {step.output}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column: Generated Deliverable Preview */}
          <div className="lg:col-span-5 flex flex-col justify-between p-6 rounded-2xl bg-[#04070e] border border-cosa-cyan/30 shadow-[0_0_30px_rgba(0,240,255,0.15)]">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cosa-emerald" />
                  <span className="text-xs font-mono font-semibold text-white">
                    OUTPUT DELIVERABLE
                  </span>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cosa-cyan/10 text-cosa-cyan border border-cosa-cyan/30">
                  {activeScenario.deliverables.type}
                </span>
              </div>

              <div>
                <h4 className="text-base font-bold text-white mb-2">
                  {activeScenario.deliverables.title}
                </h4>
                <div className="p-4 rounded-xl bg-[#0d172a] border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-line leading-relaxed overflow-x-auto">
                  {activeScenario.deliverables.preview}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-cosa-cyan/5 border border-cosa-cyan/20 text-xs text-slate-300 space-y-1.5">
                <div className="flex items-center gap-2 text-cosa-cyan font-semibold">
                  <Zap className="w-4 h-4" />
                  <span>Điểm Vượt Trội của COSA OS:</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Toàn bộ kết quả được lưu trữ đồng bộ vào Postgres pgvector và liên kết tự động tới các module Tasks, Workflows, CRM mà không cần thao tác copy-paste thủ công.
                </p>
              </div>
            </div>

            <div className="pt-6">
              <button
                onClick={() => onOpenLeadModal(`playground_${activeScenario.id}`)}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-cosa-cyan to-cosa-blue text-slate-950 font-bold text-sm shadow-[0_0_20px_rgba(0,240,255,0.4)] hover:shadow-[0_0_30px_rgba(0,240,255,0.6)] transition-all flex items-center justify-center gap-2 transform active:scale-95"
              >
                <Sparkles className="w-4 h-4 text-slate-950" />
                <span>Thử Nghiệm Kịch Bản Của Doanh Nghiệp Bạn</span>
                <ArrowRight className="w-4 h-4 text-slate-950" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
