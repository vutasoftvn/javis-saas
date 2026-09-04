"use client";

import React from "react";
import {
  Sparkles,
  ShieldCheck,
  Zap,
  GraduationCap,
} from "lucide-react";
import { EarlyAccessForm } from "../forms/EarlyAccessForm";

interface LeadFormSectionProps {
  onSuccess?: () => void;
}

export const LeadFormSection: React.FC<LeadFormSectionProps> = ({ onSuccess }) => {
  return (
    <section id="contact-form" className="py-24 bg-[#070c18] relative overflow-hidden border-t border-cosa-border">
      {/* Glow Aura */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-cosa-cyan/10 blur-[180px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          {/* Left Column: Value Prop */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
              <Sparkles className="w-3.5 h-3.5" />
              <span>CHƯƠNG TRÌNH TRẢI NGHIỆM SỚM · 100% MIỄN PHÍ</span>
            </div>

            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
              Sẵn Sàng Trải Nghiệm{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
                Hệ Điều Hành Tự Trị?
              </span>
            </h2>

            <p className="text-slate-300 text-base leading-relaxed">
              Dành cho mọi đối tượng — từ học sinh, sinh viên nghiên cứu, Solo Creator đến các Startup và doanh nghiệp. Đăng ký thông tin để nhận quyền truy cập sớm nhất.
            </p>

            <div className="space-y-4 pt-2">
              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-emerald/40">
                <div className="p-2 rounded-xl bg-cosa-emerald/10 text-cosa-emerald shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Chính Sách Gói Free 100% 0đ</h4>
                  <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">
                    Mỗi tài khoản được khởi tạo tối đa <strong>01 Không gian làm việc (Workspace)</strong> &amp; <strong>01 Dự án (Project)</strong>. Miễn phí trọn đời giai đoạn khảo sát chân dung, phân tích dự án &amp; lập PRD 12 tuần.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-border">
                <div className="p-2 rounded-xl bg-cosa-cyan/10 text-cosa-cyan shrink-0">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Bao Hàm Cả Học Sinh &amp; Sinh Viên</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Hỗ trợ tối đa cho việc làm đồ án, luận văn, thử nghiệm ý tưởng khởi nghiệp với sự trợ giúp từ 6 Chuyên viên AI.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-border">
                <div className="p-2 rounded-xl bg-cosa-sky/10 text-cosa-sky shrink-0">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Không Cần Mã · Kích Hoạt 1-Click</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Không rào cản mã thẻ. Khi hệ thống chính thức mở cổng, bạn sẽ nhận được Magic Link kích hoạt tài khoản ngay tức thì.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 rounded-2xl bg-[#080f1e] border border-cosa-border">
                <div className="p-2 rounded-xl bg-cosa-emerald/10 text-cosa-emerald shrink-0">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Bảo Mật Chuẩn Zero Data Retention</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Dữ liệu dự án của bạn hoàn toàn bảo mật, không dùng để huấn luyện bất kỳ mô hình công cộng nào.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Inherited Form Component */}
          <div className="lg:col-span-7">
            <div className="p-8 sm:p-10 rounded-3xl bg-[#080f1e]/95 border border-cosa-cyan/30 shadow-[0_0_50px_rgba(0,240,255,0.15)] backdrop-blur-2xl">
              <EarlyAccessForm
                variant="full"
                initialSource="landing_bottom_section"
                onSuccess={() => {
                  if (onSuccess) onSuccess();
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};


