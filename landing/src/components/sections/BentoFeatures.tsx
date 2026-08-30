import React from "react";
import {
  Users,
  Mic,
  Database,
  Target,
  Layers,
  FileSpreadsheet,
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
            <span>4 CLUSTERS & AGENT PLATFORM</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            5 Trụ Cột Đột Phá Của{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
              Hệ Điều Hành COSA OS
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Không chỉ là những chatbot AI độc lập, COSA OS là hệ điều hành doanh nghiệp hoàn chỉnh, kết nối liền mạch giữa Chiến lược, Nhân sự, Tài chính và Khách hàng.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-12 gap-6">
          {/* Card 1: Unified Workforce (Large 8 cols) */}
          <div className="lg:col-span-8 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="absolute top-0 right-0 w-80 h-80 bg-cosa-cyan/10 rounded-bl-full blur-2xl pointer-events-none" />

            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-cyan to-cosa-blue text-slate-950 font-bold shadow-[0_0_20px_rgba(0,240,255,0.4)]">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-cyan tracking-wider">Trụ Cột 01</span>
                <h3 className="text-xl sm:text-2xl font-bold text-white">
                  Lực Lượng Lao Động Hợp Nhất (Unified Workforce)
                </h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm sm:text-base leading-relaxed mb-6">
              Mô hình <strong className="text-white">WorkforceMember</strong> độc bản: Đưa nhân sự Người thật và Chuyên viên AI vào cùng một cơ cấu tổ chức, phân nhiệm rõ ràng theo 3 cấp độ tự chủ: <span className="text-cosa-cyan font-mono font-semibold">L0 (Quan sát)</span>, <span className="text-cosa-sky font-mono font-semibold">L1 (Đề xuất)</span> và <span className="text-cosa-emerald font-mono font-semibold">L2 (Thực thi)</span>.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 font-mono text-xs">
              {[
                { title: "CSO Iris", desc: "Giám đốc Chiến lược & OKRs 12 tuần", color: "text-cosa-cyan" },
                { title: "CMO Nova", desc: "Tăng trưởng & Marketing 360", color: "text-cosa-sky" },
                { title: "VP Sales Rex", desc: "Pipeline B2B & Chấm điểm Lead ICP", color: "text-cosa-emerald" },
                { title: "CTO Nexus", desc: "Phân bổ Engineering Tasks & Sandbox", color: "text-cosa-violet" },
                { title: "Legal Lex", desc: "Thẩm định Hợp đồng & Tuân thủ", color: "text-cosa-amber" },
                { title: "CFO Apex", desc: "Sổ cái Kế toán TT88 & Dòng tiền", color: "text-rose-400" },
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
                  <h3 className="text-xl font-bold text-white">LiveKit Realtime Voice</h3>
                </div>
              </div>

              <p className="text-slate-300 text-sm leading-relaxed mb-4">
                Tương tác giọng nói hai chiều <strong className="text-white">Full-duplex</strong> với độ trễ siêu thấp dưới 300ms, hỗ trợ ngắt lời tự nhiên và điều khiển toàn bộ ứng dụng qua khẩu lệnh tiếng Việt.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d172a] border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Độ Trễ Phản Hồi</span>
                <span className="text-cosa-emerald font-bold">&lt; 280ms</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Ngắt Lời Tự Nhiên</span>
                <span className="text-cosa-cyan">Barge-in VAD</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Voice Tools</span>
                <span className="text-white">Nav · Ask · Approve</span>
              </div>
            </div>
          </div>

          {/* Card 3: Operations & 12-Week Year (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-violet to-indigo-600 text-white font-bold shadow-[0_0_20px_rgba(139,92,246,0.4)]">
                <Target className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-violet tracking-wider">Trụ Cột 03</span>
                <h3 className="text-xl font-bold text-white">Chiến Lược 12 Tuần & OKRs</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              Phương pháp thực thi <strong className="text-white">12-Week Year</strong> chuẩn xác: Phân rã Tầm nhìn chiến lược → OKRs → Initiatives → Phân bổ Tasks Kanban.
            </p>

            <ul className="space-y-2 text-xs text-slate-400 font-mono">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-violet" />
                <span>Tự động nhận diện điểm nghẽn (Blockers)</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-violet" />
                <span>Theo dõi Task Dependencies thời gian thực</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-violet" />
                <span>Báo cáo tiến độ CEO Brief hàng tuần</span>
              </li>
            </ul>
          </div>

          {/* Card 4: Finance TT88 & Governance (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-amber to-orange-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(245,158,11,0.4)]">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-amber tracking-wider">Trụ Cột 04</span>
                <h3 className="text-xl font-bold text-white">Kế Toán TT88 & Phê Duyệt</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              Sổ cái tài chính chuẩn mực <strong className="text-white">Thông tư 88 / TT58</strong>. Dự báo dòng tiền, Runway, Burn rate đi kèm <strong className="text-white">Chốt chặn Phê duyệt rủi ro</strong>.
            </p>

            <ul className="space-y-2 text-xs text-slate-400 font-mono">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-amber" />
                <span>Human-in-the-loop: Phê duyệt trước khi chi</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-amber" />
                <span>Cảnh báo thâm hụt ngân sách tự động</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-amber" />
                <span>Nhật ký kiểm toán mật mã không thể sửa xóa</span>
              </li>
            </ul>
          </div>

          {/* Card 5: Enterprise Vault & On-Premise (4 cols) */}
          <div className="lg:col-span-4 p-8 rounded-3xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-cosa-emerald to-teal-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(16,185,129,0.4)]">
                <Database className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase text-cosa-emerald tracking-wider">Trụ Cột 05</span>
                <h3 className="text-xl font-bold text-white">Bảo Mật On-Premise & Vault</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              Chủ quyền dữ liệu tối thượng với <strong className="text-white">PostgreSQL Local Data Plane</strong> và <strong className="text-white">MinIO Vault</strong>. Tìm kiếm tài liệu nội bộ qua pgvector RAG mà không lo rò rỉ.
            </p>

            <ul className="space-y-2 text-xs text-slate-400 font-mono">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-emerald" />
                <span>Zero Data Retention: Không dùng train model</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-emerald" />
                <span>Snowflake 64-bit ID B-Tree chuẩn ngân hàng</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-emerald" />
                <span>Cài đặt 1 lệnh trên macOS/Linux/Docker</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};
