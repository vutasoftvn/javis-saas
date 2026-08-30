"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  Target,
  Zap,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  type LucideIcon,
  Clock
} from "lucide-react";

interface Scenario {
  id: string;
  title: string;
  category: string;
  icon: LucideIcon;
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
      id: "strategy-12wy",
      title: "Chu Kỳ Chiến Lược 12 Tuần & Phân Rã OKRs",
      category: "Chiến Lược & Điều Hành Vận Hành",
      icon: Target,
      agentsInvolved: ["CSO Iris", "CTO Nexus", "CFO Apex"],
      prompt: "Mục tiêu: Tăng trưởng 200% MRR trong chu kỳ 12 tuần tới cho gói B2B SaaS On-Premise.",
      executionSteps: [
        {
          agent: "CSO Iris",
          role: "Giám Đốc Chiến Lược",
          action: "Phân tích ma trận cạnh tranh & Xây dựng OKRs 12 tuần",
          output: "Xác định 3 Objectives trọng tâm và 9 Key Results đo lường theo từng tuần.",
          status: "Hoàn thành trong 1.1s",
        },
        {
          agent: "CTO Nexus",
          role: "Kiến Trúc Sư Giải Pháp",
          action: "Phân rã 14 Engineering Tasks & Thiết lập Task Dependencies",
          output: "Liên kết trực tiếp OKRs vào bảng Kanban, gán deadline và phát hiện 2 điểm nghẽn tiềm ẩn.",
          status: "Hoàn thành trong 0.8s",
        },
        {
          agent: "CFO Apex",
          role: "Giám Đốc Tài Chính",
          action: "Mô phỏng ngân sách chi tiêu & Dự báo dòng tiền thặng dư",
          output: "Dự toán Runway tăng thêm 5.2 tháng, thiết lập hạn mức chi tiêu tự động.",
          status: "Hoàn thành trong 0.9s",
        },
      ],
      deliverables: {
        title: "Kế Hoạch Thực Thi 12-Week Year Hoàn Chỉnh",
        type: "Strategic Matrix & Dependency Tree",
        preview: "Objective: Mở rộng 50 khách hàng Enterprise On-Premise\n  ├─ KR1: Tỷ lệ chuyển đổi Demo sang hợp đồng đạt 42%\n  ├─ KR2: Thời gian triển khai Local Data Plane < 24 giờ\n  └─ KR3: Dòng tiền thuần đạt mức thặng dư 1.2 tỷ VNĐ",
      },
    },
    {
      id: "commercial-crm",
      title: "Phễu Bán Hàng B2B, Chấm Điểm ICP & Hợp Đồng",
      category: "Kinh Doanh & Chăm Sóc Khách Hàng",
      icon: TrendingUp,
      agentsInvolved: ["VP Sales Rex", "CMO Nova", "Legal Lex"],
      prompt: "Xử lý 150 khách hàng tiềm năng vừa đăng ký sự kiện, phân loại ICP và lập dự thảo hợp đồng.",
      executionSteps: [
        {
          agent: "VP Sales Rex",
          role: "VP Enterprise Sales",
          action: "Chấm điểm Lead ICP 360 độ & Phân bổ tài khoản",
          output: "Lọc ra 32 khách hàng doanh nghiệp quy mô >50 nhân sự với điểm ICP > 85.",
          status: "Hoàn thành trong 1.3s",
        },
        {
          agent: "CMO Nova",
          role: "Growth & Marketing Lead",
          action: "Cá nhân hóa kịch bản tiếp cận theo ngành nghề",
          output: "Tạo 3 luồng email cá nhân hóa và thông báo lịch hẹn demo qua Zalo OA.",
          status: "Hoàn thành trong 0.7s",
        },
        {
          agent: "Legal Lex",
          role: "Luật Sư Doanh Nghiệp",
          action: "Rà soát điều khoản NDA và dự thảo hợp đồng cung ứng",
          output: "Đồng bộ mẫu hợp đồng tuân thủ pháp luật Việt Nam, đánh dấu các điều khoản rủi ro cần lưu ý.",
          status: "Hoàn thành trong 1.2s",
        },
      ],
      deliverables: {
        title: "Báo Cáo Pipeline Bán Hàng & Hợp Đồng Mẫu",
        type: "B2B Deal Pipeline & Contract Draft",
        preview: "Pipeline Value: 3.8 tỷ VNĐ (Weighted: 2.1 tỷ VNĐ)\n  ├─ 32 Qualified Enterprise Leads\n  ├─ 18 Lịch Demo đã xác nhận qua hệ thống\n  └─ 6 Hợp đồng NDA đang chờ phê duyệt điện tử",
      },
    },
    {
      id: "finance-voice",
      title: "Kiểm Soát Kế Toán Thông tư 58/TT-BTC & Duyệt Chi Bằng Giọng Nói",
      category: "Tài Chính & Quản Trị Phê Duyệt",
      icon: ShieldCheck,
      agentsInvolved: ["CFO Apex", "Trợ Lý AI", "Founder / CEO"],
      prompt: "Khẩu lệnh: “COSA, kiểm tra dòng tiền tuần này và phê duyệt ngân sách máy chủ 15 triệu.”",
      executionSteps: [
        {
          agent: "CFO Apex",
          role: "Giám Đốc Tài Chính Thông tư 58/TT-BTC",
          action: "Trích xuất sổ cái thu chi & Đánh giá tác động dòng tiền",
          output: "Số dư hiện tại 850M VNĐ. Khoản chi 15M nằm trong định mức dự phòng quý.",
          status: "Hoàn thành trong 0.5s",
        },
        {
          agent: "Governance Gate",
          role: "Human-in-the-loop Engine",
          action: "Tạo yêu cầu phê duyệt bảo mật (REQUIRE_APPROVAL)",
          output: "Khóa giao dịch vào checkpoint cryptographic audit log để chờ chữ ký.",
          status: "Hoàn thành trong 0.2s",
        },
        {
          agent: "Trợ Lý AI",
          role: "Trợ Lý Điều Hành Giọng Nói & Chat",
          action: "Phản hồi trực tiếp & Tiếp nhận lệnh 'Đồng ý phê duyệt'",
          output: "Xác thực bảo mật, mở khóa giao dịch và gửi ủy nhiệm chi tự động.",
          status: "Hoàn thành trong 0.3s (Độ trễ <280ms)",
        },
      ],
      deliverables: {
        title: "Biên Bản Phê Duyệt Tài Chính Mã Hóa",
        type: "Cryptographic Audit Ledger",
        preview: "Transaction: #TX-98402 (Chi phí hạ tầng Server)\n  ├─ Trạng thái: APPROVED qua Giọng Nói Founder\n  ├─ Checkpoint: 8492049182390184 (Snowflake ID)\n  └─ Cập nhật tự động vào sổ cái Kế toán Thông tư 58/TT-BTC",
      },
    },
  ];

  const [activeScenario, setActiveScenario] = useState<Scenario>(scenarios[0]);
  const [isRunning, setIsRunning] = useState(false);
  const [completed, setCompleted] = useState(true);

  const handleRunSimulation = () => {
    setIsRunning(true);
    setCompleted(false);
    setTimeout(() => {
      setIsRunning(false);
      setCompleted(true);
    }, 1200);
  };

  return (
    <section id="playground" className="py-24 bg-[#070c18] relative overflow-hidden border-t border-cosa-border">
      {/* Background Aura */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-96 h-96 bg-cosa-cyan/5 blur-[160px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            <span>REAL-WORLD BUSINESS PLAYGROUND</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Mô Phỏng Thực Tế:{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
              Doanh Nghiệp Chạy Tự Trị
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Chọn 1 kịch bản dưới đây để thấy cách các Chuyên viên AI phối hợp giải quyết bài toán nghiệp vụ phức tạp chỉ trong vài giây.
          </p>
        </div>

        {/* Scenario Selector Tabs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
          {scenarios.map((sc) => {
            const Icon = sc.icon;
            const isSelected = activeScenario.id === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => {
                  setActiveScenario(sc);
                  setCompleted(true);
                }}
                className={`p-5 rounded-2xl text-left transition-all duration-300 relative border ${
                  isSelected
                    ? "bg-[#0d172a] border-cosa-cyan shadow-[0_0_25px_rgba(0,240,255,0.2)]"
                    : "bg-[#080f1e]/80 border-cosa-border hover:border-cosa-cyan/40"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2.5 rounded-xl ${isSelected ? "bg-cosa-cyan text-slate-950" : "bg-slate-800 text-slate-300"}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {sc.agentsInvolved.length} Chuyên viên AI
                  </span>
                </div>
                <div className="text-xs font-mono text-cosa-cyan mb-1">{sc.category}</div>
                <div className="text-sm font-bold text-white leading-snug">{sc.title}</div>
              </button>
            );
          })}
        </div>

        {/* Execution Showcase */}
        <div className="rounded-3xl bg-[#080f1e] border border-cosa-border/80 shadow-2xl p-6 sm:p-8 backdrop-blur-xl">
          {/* Prompt Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <span className="w-2 h-2 rounded-full bg-cosa-cyan" />
                <span>YÊU CẦU ĐIỀU HÀNH ĐẦU VÀO</span>
              </div>
              <p className="text-base sm:text-lg font-semibold text-white">
                {activeScenario.prompt}
              </p>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <button
                onClick={handleRunSimulation}
                disabled={isRunning}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-bold font-mono bg-cosa-cyan/20 text-cosa-cyan border border-cosa-cyan/50 hover:bg-cosa-cyan hover:text-slate-950 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isRunning ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-cosa-cyan border-t-transparent rounded-full animate-spin" />
                    <span>Đang điều phối Swarm...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>Mô Phỏng Lại</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Execution Steps */}
          <div className="py-6 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Steps stream */}
            <div className="lg:col-span-7 space-y-4">
              <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                Nhật Ký Điều Phối Chuyên Viên (Workforce Dispatch):
              </div>

              <div className="space-y-3">
                {activeScenario.executionSteps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`p-4 rounded-2xl bg-[#0d172a] border transition-all ${
                      completed ? "border-slate-800" : "border-cosa-cyan/30 animate-pulse"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-cosa-cyan font-mono">{step.agent}</span>
                        <span className="text-[11px] text-slate-400">({step.role})</span>
                      </div>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{step.status}</span>
                      </span>
                    </div>
                    <div className="text-xs font-medium text-slate-300 mb-1">{step.action}</div>
                    <div className="text-xs text-slate-400 bg-[#070c18] p-2.5 rounded-xl font-mono text-[11px] border border-slate-900">
                      ❯ {step.output}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Deliverable Result Preview */}
            <div className="lg:col-span-5 space-y-4">
              <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                Kết Quả Thực Thi Trực Tiếp (Actionable Deliverable):
              </div>

              <div className="p-5 rounded-2xl bg-[#04070e] border border-cosa-cyan/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>{activeScenario.deliverables.title}</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cosa-cyan/15 text-cosa-cyan border border-cosa-cyan/30">
                    {activeScenario.deliverables.type}
                  </span>
                </div>

                <pre className="p-3.5 rounded-xl bg-[#0d172a] text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre leading-relaxed border border-slate-800">
                  {activeScenario.deliverables.preview}
                </pre>

                <div className="pt-2">
                  <button
                    onClick={() => onOpenLeadModal(`playground_${activeScenario.id}`)}
                    className="w-full py-3 rounded-xl font-bold text-xs text-slate-950 bg-gradient-to-r from-cosa-cyan to-cosa-sky hover:from-white hover:to-cosa-cyan transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(0,240,255,0.3)]"
                  >
                    <span>Áp Dụng Kịch Bản Này Cho Doanh Nghiệp Bạn</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
