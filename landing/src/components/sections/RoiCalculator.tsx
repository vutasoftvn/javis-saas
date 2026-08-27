"use client";

import React, { useState } from "react";
import {
  Calculator,
  Sparkles,
  Clock,
  DollarSign,
  ArrowRight,
  CheckCircle2
} from "lucide-react";

interface RoiCalculatorProps {
  onOpenLeadModal: (source?: string) => void;
}

export const RoiCalculator: React.FC<RoiCalculatorProps> = ({ onOpenLeadModal }) => {
  const [teamSize, setTeamSize] = useState<number>(15);
  const [avgSalary, setAvgSalary] = useState<number>(20); // Triệu VND / tháng

  // Calculations
  // Giả định: COSA OS tiết kiệm trung bình 3.5 giờ làm việc mỗi nhân viên/ngày (khoảng 35% quỹ thời gian)
  const hoursSavedPerMonth = Math.round(teamSize * 3.5 * 22);
  const monthlyCostSavings = Math.round(teamSize * avgSalary * 0.35); // Triệu VND
  const yearlyCostSavings = monthlyCostSavings * 12; // Triệu VND

  const formatVnd = (valInMillions: number) => {
    if (valInMillions >= 1000) {
      return `${(valInMillions / 1000).toFixed(1)} Tỷ VNĐ`;
    }
    return `${valInMillions.toLocaleString("vi-VN")} Triệu VNĐ`;
  };

  return (
    <section id="roi-calculator" className="py-24 bg-[#04070e] relative overflow-hidden">
      {/* Background Accent */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-96 bg-cosa-emerald/5 blur-[160px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Title */}
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-emerald/10 border border-cosa-emerald/30 text-cosa-emerald text-xs font-mono">
            <Calculator className="w-3.5 h-3.5" />
            <span>INTERACTIVE ROI SIMULATOR</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Tính Toán Hiệu Quả Đầu Tư &{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-emerald to-cosa-cyan inline-block pt-1">
              Chi Phí Tiết Kiệm Được
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Kéo thanh trượt theo quy mô doanh nghiệp để thấy rõ số giờ làm việc giải phóng và chi phí vận hành cắt giảm hàng năm.
          </p>
        </div>

        {/* Calculator Main Box */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 bg-[#080f1e]/90 border border-cosa-border rounded-3xl p-6 sm:p-10 backdrop-blur-2xl shadow-2xl">
          {/* Sliders Input (7 cols) */}
          <div className="lg:col-span-7 space-y-8 flex flex-col justify-center">
            {/* Slider 1: Team Size */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-slate-200">
                  Quy mô nhân sự doanh nghiệp:
                </label>
                <span className="text-lg font-bold font-mono text-cosa-cyan px-3 py-1 rounded-lg bg-[#0d172a] border border-slate-700">
                  {teamSize} Nhân sự
                </span>
              </div>
              <input
                type="range"
                min="3"
                max="150"
                step="1"
                value={teamSize}
                onChange={(e) => setTeamSize(Number(e.target.value))}
                className="w-full h-2.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cosa-cyan"
              />
              <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                <span>3 người (Seed Startup)</span>
                <span>50 người (SME)</span>
                <span>150+ người (Scaleup)</span>
              </div>
            </div>

            {/* Slider 2: Average Salary */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-slate-200">
                  Mức lương trung bình / nhân viên:
                </label>
                <span className="text-lg font-bold font-mono text-cosa-emerald px-3 py-1 rounded-lg bg-[#0d172a] border border-slate-700">
                  {avgSalary} Triệu VNĐ / tháng
                </span>
              </div>
              <input
                type="range"
                min="10"
                max="80"
                step="5"
                value={avgSalary}
                onChange={(e) => setAvgSalary(Number(e.target.value))}
                className="w-full h-2.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cosa-emerald"
              />
              <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                <span>10 Triệu/tháng</span>
                <span>40 Triệu/tháng</span>
                <span>80 Triệu/tháng</span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d172a] border border-slate-800 space-y-2 text-xs text-slate-400">
              <div className="flex items-center gap-2 text-slate-200 font-semibold">
                <CheckCircle2 className="w-4 h-4 text-cosa-emerald" />
                <span>Cơ sở tính toán thực tế:</span>
              </div>
              <p>
                Dựa trên dữ liệu triển khai của các doanh nghiệp sử dụng COSA OS: Giảm 60% thời gian họp báo cáo, tự động hóa 80% công việc soạn thảo kế hoạch, phân tích hợp đồng và tạo chiến dịch tiếp thị.
              </p>
            </div>
          </div>

          {/* Results Display (5 cols) */}
          <div className="lg:col-span-5 flex flex-col justify-between p-6 sm:p-8 rounded-2xl bg-gradient-to-b from-[#0d172a] to-[#04070e] border border-cosa-emerald/40 shadow-[0_0_40px_rgba(16,185,129,0.15)]">
            <div className="space-y-6">
              <div className="text-xs font-mono uppercase tracking-wider text-cosa-emerald pb-3 border-b border-slate-800 flex items-center justify-between">
                <span>KẾT QUẢ DỰ BÁO ROI</span>
                <span className="text-slate-400">HOÀN VỐN &lt; 30 NGÀY</span>
              </div>

              {/* Metric 1 */}
              <div>
                <div className="text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-cosa-cyan" />
                  <span>Quỹ thời gian giải phóng mỗi tháng:</span>
                </div>
                <div className="text-3xl font-extrabold text-white font-mono">
                  {hoursSavedPerMonth.toLocaleString("vi-VN")}{" "}
                  <span className="text-sm font-sans font-normal text-cosa-cyan">Giờ làm việc</span>
                </div>
              </div>

              {/* Metric 2 */}
              <div className="pt-2 border-t border-slate-800/80">
                <div className="text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                  <DollarSign className="w-3.5 h-3.5 text-cosa-emerald" />
                  <span>Chi phí vận hành tiết kiệm mỗi năm:</span>
                </div>
                <div className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cosa-emerald via-teal-300 to-white font-mono">
                  {formatVnd(yearlyCostSavings)}
                </div>
              </div>

              {/* Extra Perks */}
              <div className="space-y-1.5 pt-2 text-xs text-slate-300 font-mono">
                <div className="flex items-center gap-2">
                  <span className="text-cosa-emerald">✓</span>
                  <span>Tăng 2.8x năng suất ra sản phẩm</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-cosa-emerald">✓</span>
                  <span>Giảm 95% tỷ lệ sót việc và trễ hạn OKR</span>
                </div>
              </div>
            </div>

            <div className="pt-8">
              <button
                onClick={() => onOpenLeadModal(`roi_calculator_size_${teamSize}`)}
                className="w-full py-4 rounded-xl bg-gradient-to-r from-cosa-emerald to-teal-400 hover:from-white hover:to-cosa-emerald text-slate-950 font-bold text-sm shadow-[0_0_25px_rgba(16,185,129,0.4)] transition-all flex items-center justify-center gap-2 transform active:scale-95"
              >
                <Sparkles className="w-4 h-4 text-slate-950" />
                <span>Nhận Báo Cáo Tư Vấn Chi Tiết Cho Doanh Nghiệp</span>
                <ArrowRight className="w-4 h-4 text-slate-950" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
