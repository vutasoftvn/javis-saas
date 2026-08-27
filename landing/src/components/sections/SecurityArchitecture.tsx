import React from "react";
import {
  ShieldCheck,
  Lock,
  Server,
  Key,
  FileCode,
  CheckCircle2,
  HardDrive,
  Cpu,
  Layers
} from "lucide-react";

export const SecurityArchitecture: React.FC = () => {
  const securityFeatures = [
    {
      icon: HardDrive,
      title: "Triển Khai On-Premise & Private VPS",
      desc: "Toàn bộ cơ sở dữ liệu Postgres, pgvector và MinIO Vault có thể tự lưu trữ tại máy chủ nội bộ hoặc Dedicated VPS Hostinger của doanh nghiệp. Bạn sở hữu 100% dữ liệu.",
    },
    {
      icon: ShieldCheck,
      title: "Chính Sách Zero-Data Retention",
      desc: "Không gửi dữ liệu huấn luyện công khai, bảo vệ tuyệt đối bí mật kinh doanh, mã nguồn và báo cáo tài chính của công ty.",
    },
    {
      icon: Key,
      title: "Snowflake 64-bit ID Standard",
      desc: "Định danh khóa chính toàn hệ thống bằng 64-bit Snowflake ID tuần tự theo thời gian, tối ưu B-tree indexing và ngăn chặn nguy cơ tấn công brute-force ID.",
    },
    {
      icon: Layers,
      title: "Phân Quyền Workspace & Brain Độc Lập",
      desc: "Kiểm tra quyền sở hữu Workspace và Brain trên từng API endpoint tại máy chủ; không bao giờ tin tưởng định danh từ client gửi lên.",
    },
    {
      icon: FileCode,
      title: "OpenSandbox Môi Trường Thực Thi Cô Lập",
      desc: "Các tác vụ sinh mã, chạy script và kiểm thử công nghệ của Agent đều được cách ly nghiêm ngặt trong Sandbox, đảm bảo an toàn tuyệt đối cho hệ thống máy chủ.",
    },
    {
      icon: Cpu,
      title: "Tối Ưu DSPy & OpenRouter Multi-Model",
      desc: "Linh hoạt lựa chọn mô hình AI cục bộ (Ollama/vLLM) hoặc đám mây bảo mật cao (Claude, DeepSeek, GPT-4o) theo chính sách an ninh từng phòng ban.",
    },
  ];

  return (
    <section id="architecture" className="py-24 bg-[#070c18] relative overflow-hidden border-t border-cosa-border">
      {/* Glow Effect */}
      <div className="absolute top-1/2 right-10 w-96 h-96 bg-cosa-cyan/5 blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-cyan/10 border border-cosa-cyan/30 text-cosa-cyan text-xs font-mono">
            <Lock className="w-3.5 h-3.5" />
            <span>ENTERPRISE SECURITY & INFRASTRUCTURE</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Kiến Trúc Chuẩn Enterprise &{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan to-cosa-blue inline-block pt-1">
              Bảo Mật Dữ Liệu Tuyệt Đối
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Được thiết kế từ gốc cho các tổ chức coi trọng an toàn thông tin, bảo mật bí mật kinh doanh và toàn quyền kiểm soát hạ tầng AI.
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {securityFeatures.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <div
                key={idx}
                className="p-6 rounded-2xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all group relative overflow-hidden"
              >
                <div className="p-3 w-fit rounded-xl bg-[#0d172a] border border-slate-800 text-cosa-cyan group-hover:bg-cosa-cyan group-hover:text-black transition-colors mb-4">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2 group-hover:text-cosa-cyan transition-colors">
                  {feat.title}
                </h3>
                <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                  {feat.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Infrastructure Topology Visualizer */}
        <div className="mt-12 p-6 sm:p-8 rounded-3xl bg-[#04070e] border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6 text-xs font-mono">
          <div className="flex items-center gap-3">
            <Server className="w-6 h-6 text-cosa-cyan shrink-0" />
            <div>
              <div className="text-white font-bold text-sm">Hạ Tầng Khép Kín (Closed-Loop Topology)</div>
              <div className="text-slate-500">FastAPI • PostgreSQL pgvector • MinIO • Docker Compose • Hostinger VPS</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-cosa-emerald">
            <CheckCircle2 className="w-4 h-4" />
            <span className="font-semibold">Đạt chuẩn triển khai On-Premise & Private Cloud</span>
          </div>
        </div>
      </div>
    </section>
  );
};
