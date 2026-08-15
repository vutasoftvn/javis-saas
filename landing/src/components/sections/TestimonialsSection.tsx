import React from "react";
import { Star, Quote, Sparkles, Building2, User } from "lucide-react";

export const TestimonialsSection: React.FC = () => {
  const reviews = [
    {
      name: "Nguyễn Minh Tuấn",
      role: "Founder & CEO, FinTech Scaleup",
      quote: "Trước đây chúng tôi mất 2 tuần mỗi quý chỉ để họp và phân bổ OKRs xuống các phòng ban. Với COSA OS, CSO Iris phân rã mục tiêu sang 40 actionable tasks và đồng bộ lên Kanban chỉ trong đúng 15 phút.",
      metric: "Tiết kiệm 80% thời gian họp",
      avatarBg: "from-cosa-cyan to-cosa-blue",
    },
    {
      name: "Lê Hoàng Nam",
      role: "Chief Operating Officer, E-commerce Logistics",
      quote: "Tính năng LiveKit Realtime Voice cho phép tôi rà soát toàn bộ số liệu doanh thu và tồn kho khi đang lái xe hoặc di chuyển giữa các kho. Độ trễ cực thấp và phản hồi vô cùng chuẩn xác.",
      metric: "Quản trị tức thời 24/7",
      avatarBg: "from-cosa-emerald to-teal-500",
    },
    {
      name: "Trần Mai Anh",
      role: "Head of Marketing & Growth, EduTech",
      quote: "Khả năng tự động sinh mã Modular Landing Page và đẩy thẳng lên Hostinger VPS giúp team của tôi thử nghiệm 5 chiến dịch tiếp thị mỗi tuần thay vì 1 chiến dịch như trước kia.",
      metric: "Tăng 5x tốc độ ra mắt chiến dịch",
      avatarBg: "from-cosa-violet to-purple-600",
    },
  ];

  return (
    <section className="py-24 bg-[#070c18] relative overflow-hidden border-t border-cosa-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            <span>REAL WORLD SUCCESS STORIES</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Được Tin Dùng Bởi Các{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan to-cosa-sky inline-block pt-1">
              Nhà Lãnh Đạo & Doanh Nghiệp Tiên Phong
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Khám phá cách các công ty công nghệ và SME chuyển đổi mô hình vận hành sang tự trị hoàn toàn.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {reviews.map((rev, idx) => (
            <div
              key={idx}
              className="p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all flex flex-col justify-between relative group"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-1 text-amber-400">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 fill-amber-400" />
                    ))}
                  </div>
                  <span className="text-[11px] font-mono text-cosa-cyan px-2 py-0.5 rounded bg-cosa-cyan/10 border border-cosa-cyan/20">
                    {rev.metric}
                  </span>
                </div>

                <Quote className="w-8 h-8 text-slate-700 mb-3" />
                <p className="text-sm text-slate-300 leading-relaxed italic mb-6">
                  “{rev.quote}”
                </p>
              </div>

              <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${rev.avatarBg} flex items-center justify-center font-bold text-slate-950 text-sm shadow-md`}>
                  {rev.name.charAt(0)}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">{rev.name}</h4>
                  <p className="text-xs text-slate-400">{rev.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
