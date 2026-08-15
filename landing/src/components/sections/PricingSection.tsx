"use client";

import React, { useState } from "react";
import { 
  Check, 
  Sparkles, 
  Zap, 
  ShieldCheck, 
  Server, 
  ArrowRight,
  Bot,
  Crown
} from "lucide-react";

interface PricingSectionProps {
  onOpenLeadModal: (source?: string) => void;
}

export const PricingSection: React.FC<PricingSectionProps> = ({ onOpenLeadModal }) => {
  const [isAnnual, setIsAnnual] = useState(true);

  const tiers = [
    {
      id: "starter",
      name: "Starter / Solo Founder",
      badge: "Dành cho Khởi Nghiệp",
      desc: "Lý tưởng cho các Founder hoặc nhóm nhỏ muốn tự động hóa công việc và gia tăng năng suất gấp 5 lần.",
      priceMonthly: "1,500,000",
      priceAnnual: "1,200,000",
      features: [
        "1 Workspace & 2 Brains độc lập",
        "3 Core AI Agents (Strategy, Tech, Sales)",
        "Kho tri thức Enterprise Vault 10GB",
        "Trò chuyện AI Stream SSE độ trễ thấp",
        "Hỗ trợ OKRs & Kanban Task Management",
        "Triển khai Docker Compose cục bộ",
      ],
      popular: false,
      ctaText: "Bắt Đầu Dùng Thử 14 Ngày",
    },
    {
      id: "growth",
      name: "Growth Company",
      badge: "Phổ Biến Nhất",
      desc: "Giải pháp toàn diện cho các công ty đang mở rộng quy mô, cần tự động hóa marketing, bán hàng và điều hành.",
      priceMonthly: "4,500,000",
      priceAnnual: "3,600,000",
      features: [
        "Không giới hạn thành viên trong công ty",
        "Trọn bộ 7 AI Agents chuyên trách",
        "LiveKit Realtime Voice Streaming",
        "Tự động sinh Modular Landing & CRM Funnel",
        "Tích hợp Hostinger VPS MCP 1-Click Deploy",
        "Kho tri thức Enterprise Vault 100GB",
        "Tối ưu hóa DSPy Prompt & DeepSeek V3",
        "Hỗ trợ kỹ thuật ưu tiên 8/5",
      ],
      popular: true,
      ctaText: "Đăng Ký Bản Growth Ngay",
    },
    {
      id: "enterprise",
      name: "Enterprise On-Premise",
      badge: "Toàn Quyền Sở Hữu",
      desc: "Dành cho tập đoàn và doanh nghiệp có yêu cầu khắt khe về bảo mật dữ liệu, cần cài đặt tại máy chủ riêng.",
      priceMonthly: "Liên hệ",
      priceAnnual: "Tùy biến",
      features: [
        "Cài đặt On-Premise 100% tại Server của bạn",
        "Zero Data Retention & Cô lập hoàn toàn",
        "Tùy chỉnh & Fine-tune AI Agent theo nghiệp vụ",
        "Tích hợp ERP, CRM nội bộ và Zalo OA Doanh Nghiệp",
        "Cam kết SLA uptime 99.99%",
        "Kỹ sư giải pháp hỗ trợ Onboarding & Bảo trì 24/7",
      ],
      popular: false,
      ctaText: "Đặt Lịch Tư Vấn Doanh Nghiệp",
    },
  ];

  return (
    <section id="pricing" className="py-24 bg-[#04070e] relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-3/4 h-96 bg-cosa-blue/5 blur-[160px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <Zap className="w-3.5 h-3.5" />
            <span>TRANSPARENT PRICING TIERS</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Đầu Tư Linh Hoạt Cho{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
              Tương Lai Doanh Nghiệp Tự Trị
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Chi phí chỉ bằng một phần nhỏ lương của một nhân viên, nhưng sở hữu sức mạnh vận hành của cả một đội ngũ chuyên gia AI hàng đầu.
          </p>

          {/* Monthly / Annual Toggle */}
          <div className="flex items-center justify-center gap-4 pt-4">
            <span className={`text-sm font-medium ${!isAnnual ? "text-white" : "text-slate-400"}`}>
              Thanh toán hàng tháng
            </span>
            <button
              onClick={() => setIsAnnual(!isAnnual)}
              className="w-14 h-8 rounded-full bg-[#0d172a] p-1 border border-slate-700 transition-colors relative"
            >
              <div
                className={`w-6 h-6 rounded-full bg-gradient-to-r from-cosa-cyan to-cosa-blue transition-transform ${
                  isAnnual ? "translate-x-6" : "translate-x-0"
                }`}
              />
            </button>
            <div className="flex items-center gap-1.5">
              <span className={`text-sm font-medium ${isAnnual ? "text-white" : "text-slate-400"}`}>
                Thanh toán theo năm
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                Tiết kiệm 20%
              </span>
            </div>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {tiers.map((tier) => (
            <div
              key={tier.id}
              className={`rounded-3xl p-8 transition-all relative flex flex-col justify-between ${
                tier.popular
                  ? "bg-[#080f1e] border-2 border-cosa-cyan shadow-[0_0_40px_rgba(0,240,255,0.25)]"
                  : "bg-[#080f1e]/80 border border-cosa-border hover:border-slate-700"
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-cosa-cyan to-cosa-blue text-slate-950 font-bold text-xs shadow-lg uppercase tracking-wider flex items-center gap-1.5">
                  <Crown className="w-3.5 h-3.5 text-slate-950 fill-slate-950" />
                  <span>{tier.badge}</span>
                </div>
              )}

              <div>
                <div className="mb-4">
                  <span className="text-xs font-mono uppercase text-cosa-cyan tracking-wider">
                    {tier.badge}
                  </span>
                  <h3 className="text-2xl font-bold text-white mt-1">{tier.name}</h3>
                  <p className="text-xs text-slate-400 mt-2 min-h-[36px]">{tier.desc}</p>
                </div>

                {/* Price Display */}
                <div className="py-6 border-y border-slate-800 my-4">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold text-white font-mono">
                      {isAnnual ? tier.priceAnnual : tier.priceMonthly}
                    </span>
                    {tier.priceMonthly !== "Liên hệ" && (
                      <span className="text-xs text-slate-400 font-mono">VNĐ / tháng</span>
                    )}
                  </div>
                  {isAnnual && tier.priceMonthly !== "Liên hệ" && (
                    <div className="text-[11px] text-slate-500 font-mono mt-1">
                      Thanh toán theo chu kỳ 12 tháng
                    </div>
                  )}
                </div>

                {/* Feature List */}
                <ul className="space-y-3 my-6 text-xs sm:text-sm text-slate-300">
                  {tier.features.map((feat, i) => (
                    <li key={i} className="flex items-start gap-2.5">
                      <div className="p-0.5 rounded-full bg-cosa-cyan/10 text-cosa-cyan shrink-0 mt-0.5">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-4">
                <button
                  onClick={() => onOpenLeadModal(`pricing_${tier.id}`)}
                  className={`w-full py-3.5 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 transform active:scale-95 ${
                    tier.popular
                      ? "bg-gradient-to-r from-cosa-cyan to-cosa-blue text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.4)] hover:shadow-[0_0_30px_rgba(0,240,255,0.6)]"
                      : "bg-[#0d172a] text-white hover:bg-slate-800 border border-slate-700 hover:border-cosa-cyan/40"
                  }`}
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{tier.ctaText}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
