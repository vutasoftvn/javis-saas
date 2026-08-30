import React from "react";
import {
  ShieldCheck,
  Lock,
  Key,
  HardDrive,
  Layers,
  FileCheck2
} from "lucide-react";

export const SecurityArchitecture: React.FC = () => {
  const securityFeatures = [
    {
      icon: HardDrive,
      title: "Triển Khai On-Premise & Local Data Plane",
      desc: "Toàn bộ cơ sở dữ liệu Postgres nghiệp vụ và MinIO Vault lưu trữ trực tiếp trên máy chủ nội bộ hoặc Private Cloud của doanh nghiệp. Bạn sở hữu 100% dữ liệu.",
    },
    {
      icon: ShieldCheck,
      title: "Chính Sách Zero-Data Retention",
      desc: "Cam kết không sử dụng dữ liệu doanh nghiệp để huấn luyện mô hình công khai, bảo vệ tuyệt đối bí mật kinh doanh, mã nguồn và báo cáo tài chính.",
    },
    {
      icon: Key,
      title: "Snowflake 64-bit ID Standard",
      desc: "Định danh khóa chính toàn hệ thống bằng 64-bit Snowflake ID tuần tự theo thời gian, tối ưu B-tree indexing và triệt tiêu nguy cơ đoán ID.",
    },
    {
      icon: Layers,
      title: "Cô Lập Đa Khách Thuê (Tenant Context)",
      desc: "Kiểm tra quyền sở hữu Workspace và Tenant trên từng API endpoint tại máy chủ; không bao giờ tin tưởng định danh từ client gửi lên.",
    },
    {
      icon: Lock,
      title: "Chốt Chặn Phê Duyệt Rủi Ro (Human-in-the-loop)",
      desc: "Các hành động chuyển tiền, phát hành hóa đơn, gửi email ra ngoài hay phân quyền đều bắt buộc ràng buộc mã phê duyệt định danh của con người (REQUIRE_APPROVAL).",
    },
    {
      icon: FileCheck2,
      title: "Chuẩn Mực Kế Toán Thông tư 58/TT-BTC & AI Governance",
      desc: "Sổ sách tài chính tương thích chuẩn Thông tư 58/TT-BTC Việt Nam, tích hợp danh mục quy định pháp lý và nhật ký kiểm toán mật mã không thể sửa đổi.",
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
            <span>ENTERPRISE SECURITY & SOVEREIGNTY</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.22] pb-2">
            Bảo Mật Cấp Doanh Nghiệp &{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue inline-block pt-1">
              Chủ Quyền Dữ Liệu Tuyệt Đối
            </span>
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Được thiết kế theo tiêu chuẩn an ninh nghiêm ngặt nhất dành cho các tổ chức tài chính, doanh nghiệp tăng trưởng và cơ quan quản lý.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {securityFeatures.map((f, i) => {
            const Icon = f.icon;
            return (
              <div
                key={i}
                className="p-6 rounded-2xl bg-[#080f1e] border border-cosa-border hover:border-cosa-cyan/40 transition-all duration-300 relative group overflow-hidden"
              >
                <div className="p-3 rounded-xl bg-[#0d172a] text-cosa-cyan w-fit mb-4 group-hover:scale-110 transition-transform">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{f.title}</h3>
                <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>

        {/* Bottom Banner */}
        <div className="mt-12 p-6 rounded-2xl bg-gradient-to-r from-[#0d172a] via-[#080f1e] to-[#0d172a] border border-cosa-cyan/30 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-cosa-cyan/20 flex items-center justify-center text-cosa-cyan shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">Kiểm Toán Bảo Mật Độc Lập & Tuân Thủ Pháp Luật Việt Nam</div>
              <div className="text-xs text-slate-400">Kiến trúc đáp ứng các quy định an toàn thông tin mạng và quy chuẩn kế toán tài chính hiện hành.</div>
            </div>
          </div>
          <div className="text-xs font-mono text-cosa-cyan whitespace-nowrap bg-cosa-cyan/10 px-4 py-2 rounded-xl border border-cosa-cyan/30">
            LOCAL DATA PLANE READY
          </div>
        </div>
      </div>
    </section>
  );
};
