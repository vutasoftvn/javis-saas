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
      a: "ChatGPT hoặc Claude là mô hình ngôn ngữ đơn lẻ, chỉ phản hồi dạng văn bản trong khung chat cá nhân. COSA OS là một Hệ điều hành doanh nghiệp tự trị toàn diện: cung cấp mô hình WorkforceMember hợp nhất nhân sự Người thật & Chuyên viên AI trên cùng một sơ đồ tổ chức, chu kỳ quản trị chiến lược 12 tuần gắn liền bảng việc Kanban, sổ cái tài chính chuẩn Thông tư 58/TT-BTC và Trợ lý AI điều hành đàm thoại hai chiều dưới 280ms.",
    },
    {
      q: "Mô hình OPC (Doanh nghiệp một người) có phù hợp không và chính sách Miễn phí phân tích dự án là gì?",
      a: "COSA OS được xây dựng hoàn hảo cho mô hình OPC (One-Person Company - Doanh nghiệp một người) và Solo Founder. Bạn được cấp trọn bộ công cụ AI để phân tích dự án, nghiên cứu chân dung người dùng (User Persona), khảo sát nghiệp vụ và lập kế hoạch chiến lược 12 tuần hoàn toàn MIỄN PHÍ TRỌN ĐỜI (0đ). Khi bạn sẵn sàng mở rộng sang giai đoạn vận hành tự trị với 6 Chuyên viên AI và sổ cái kế toán Thông tư 58/TT-BTC, bạn mới cần cân nhắc nâng cấp lên các gói tiếp theo.",
    },
    {
      q: "Dữ liệu kinh doanh của công ty tôi có được bảo mật và tự lưu trữ không?",
      a: "Có. COSA OS triển khai theo kiến trúc Hybrid: Local Data Plane (PostgreSQL + MinIO Vault) chạy trực tiếp tại máy chủ nội bộ hoặc Private Cloud của doanh nghiệp bạn. Chúng tôi cam kết chính sách Zero-Data Retention: dữ liệu doanh nghiệp không bao giờ bị sử dụng để huấn luyện mô hình bên thứ ba, bạn làm chủ 100% dữ liệu.",
    },
    {
      q: "Các AI Agent có tự ý chi tiền hay ra quyết định rủi ro ngoài tầm kiểm soát không?",
      a: "Tuyệt đối không. Hệ thống áp dụng cơ chế Human-in-the-loop Governance qua 3 cấp độ tự chủ: L0 (Chỉ quan sát & lập báo cáo), L1 (Đề xuất kế hoạch), L2 (Thực thi giới hạn). Mọi hành động tài chính, duyệt chi ngân sách, xuất hợp đồng pháp lý hay gửi email quan trọng đều bắt buộc phải có con người phê duyệt (REQUIRE_APPROVAL) được gắn mã chữ ký cryptographic audit log.",
    },
    {
      q: "Hệ thống có tương thích với chuẩn mực kế toán Việt Nam (Thông tư 58/TT-BTC) không?",
      a: "Có. Cụm dịch vụ Finance-Legal của COSA OS được tích hợp sẵn danh mục chế độ kế toán theo Thông tư 58/TT-BTC của Bộ Tài chính Việt Nam, hỗ trợ theo dõi kỳ kế toán, sổ chi tiết doanh thu chi phí, dự báo dòng tiền thuần, Runway và mức độ đốt tiền (Burn rate) theo thời gian thực.",
    },
    {
      q: "Làm thế nào để đăng ký Early Access và nhận tài khoản trải nghiệm 14 ngày?",
      a: "Bạn chỉ cần điền thông tin vào Form Đăng Ký Early Access trên trang web. Hệ thống sẽ tự động cấp Mã Thẻ VIP Early Access và gửi email xác nhận tức thì qua Resend API. Chuyên gia giải pháp của COSA OS sẽ liên hệ trong vòng 2-4 giờ làm việc để cấp tài khoản Workspace và đồng hành thiết lập kịch bản demo riêng cho doanh nghiệp bạn.",
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
            Mọi điều bạn cần biết về kiến trúc, bảo mật và chương trình trải nghiệm sớm COSA OS.
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
                  <div className="px-6 pb-6 pt-1 text-sm text-slate-300 leading-relaxed border-t border-slate-800/60 bg-[#04070e]/50 animate-fadeIn">
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
