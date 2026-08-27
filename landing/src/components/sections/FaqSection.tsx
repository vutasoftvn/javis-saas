"use client";

import React, { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";

interface FaqItem {
  q: string;
  a: string;
}

export const FaqSection: React.FC = () => {
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  const faqs: FaqItem[] = [
    {
      q: "COSA OS khác gì so với việc sử dụng ChatGPT hay Claude thông thường?",
      a: "ChatGPT hoặc Claude là mô hình ngôn ngữ đơn lẻ phục vụ hỏi đáp cá nhân. COSA OS là một Hệ điều hành doanh nghiệp hoàn chỉnh: cung cấp 7 AI Agents chuyên trách phối hợp với nhau, kho tri thức RAG pgvector bảo mật riêng, bảng điều phối OKRs nối thẳng Kanban, trợ lý giọng nói LiveKit Realtime và hệ thống tạo Landing Page nối tự động vào CRM Postgres.",
    },
    {
      q: "Dữ liệu kinh doanh và tài liệu của công ty có được bảo mật tuyệt đối không?",
      a: "Có. COSA OS hỗ trợ mô hình On-Premise / Dedicated VPS riêng biệt và tuân thủ nguyên tắc Zero Data Retention. Tài liệu trong Vault được lưu trên MinIO nội bộ, vector embeddings nằm trong cơ sở dữ liệu PostgreSQL của bạn và không bao giờ bị sử dụng để huấn luyện mô hình công cộng.",
    },
    {
      q: "Thời gian cài đặt và đưa vào vận hành thực tế mất bao lâu?",
      a: "Với bản Cloud / Hostinger VPS 1-Click Deploy, bạn chỉ mất chưa đầy 15 phút để khởi chạy toàn bộ cụm dịch vụ (Brain API, Worker, Database). Việc nạp tài liệu công ty vào Enterprise Vault diễn ra tự động với bộ xử lý embedding nền.",
    },
    {
      q: "COSA OS có kết nối được với các kênh bán hàng như Zalo OA, Email, Webhook không?",
      a: "Có. COSA OS tích hợp sẵn các đầu nối Zalo OA, kênh gửi nhận email tự động qua Resend/SMTP, webhooks hai chiều và MCP Servers giúp doanh nghiệp dễ dàng đồng bộ dữ liệu khách hàng từ mọi nguồn.",
    },
    {
      q: "Doanh nghiệp có thể tùy chỉnh các AI Agent theo nghiệp vụ riêng không?",
      a: "Hoàn toàn có thể. Nền tảng tích hợp bộ tối ưu hóa Prompt DSPy MIPROv2 và cho phép tùy biến vai trò, mục tiêu, quyền truy cập tài liệu và quyền thực thi công cụ của từng Agent theo đúng cấu trúc phòng ban của bạn.",
    },
  ];

  return (
    <section id="faq" className="py-24 bg-[#04070e] relative overflow-hidden">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center space-y-4 mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>FREQUENTLY ASKED QUESTIONS</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Câu Hỏi{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan to-cosa-sky inline-block pt-1">
              Thường Gặp
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Mọi điều bạn cần biết về kiến trúc, bảo mật và khả năng mở rộng của COSA OS.
          </p>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => {
            const isOpen = openIdx === idx;
            return (
              <div
                key={idx}
                className="rounded-2xl bg-[#080f1e] border border-cosa-border overflow-hidden transition-all"
              >
                <button
                  onClick={() => setOpenIdx(isOpen ? null : idx)}
                  className="w-full p-6 text-left flex items-center justify-between gap-4 hover:bg-slate-900/50 transition-colors"
                >
                  <span className="text-base sm:text-lg font-bold text-white">
                    {faq.q}
                  </span>
                  <div className={`p-1.5 rounded-lg bg-[#0d172a] text-cosa-cyan transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`}>
                    <ChevronDown className="w-5 h-5" />
                  </div>
                </button>
                {isOpen && (
                  <div className="px-6 pb-6 pt-1 text-sm text-slate-300 leading-relaxed border-t border-slate-800/60 bg-[#04070e]/50">
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
