import type { Metadata } from "next";
import { Be_Vietnam_Pro, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "COSA OS — Hệ Điều Hành Doanh Nghiệp AI Tự Trị & Mô Hình OPC",
  description:
    "Hệ điều hành doanh nghiệp AI thế hệ mới: Hợp nhất nhân sự Người thật & AI Agents (WorkforceMember) cho mô hình OPC (Doanh nghiệp một người) & SME. Miễn phí 100% cho giai đoạn phân tích dự án & người dùng.",
  keywords: [
    "COSA OS",
    "OPC",
    "Doanh nghiệp một người",
    "One-Person Company",
    "Solo Founder AI",
    "Miễn phí phân tích dự án",
    "Hệ điều hành doanh nghiệp AI",
    "Unified Workforce",
    "WorkforceMember",
    "12-Week Year",
    "OKRs AI",
    "Kế toán Thông tư 58/TT-BTC",
    "Trợ Lý AI",
    "PostgreSQL Local Data Plane",
    "Early Access Waitlist",
  ],
  authors: [{ name: "MIVA Corp" }],
  creator: "MIVA Corp",
  publisher: "MIVA Corp",
  openGraph: {
    title: "COSA OS — The AI Operating System for Startups & Founders",
    description:
      "Tự trị hóa vận hành doanh nghiệp với đội ngũ Chuyên viên AI hợp nhất, quản trị chiến lược 12 tuần, kế toán Thông tư 58/TT-BTC và Trợ lý AI điều hành thông minh.",
    type: "website",
    locale: "vi_VN",
  },
  twitter: {
    card: "summary_large_image",
    title: "COSA OS — Autonomous Company AI Platform",
    description:
      "Hệ điều hành doanh nghiệp AI tự trị đầu tiên tại Việt Nam với Bot Enterprise, pgvector RAG và kế toán Thông tư 88.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="dark scroll-smooth">
      <body
        className={`${beVietnamPro.variable} ${jetbrainsMono.variable} font-sans antialiased bg-[#070c18] text-white selection:bg-[#00f0ff] selection:text-[#04070e]`}
      >
        {children}
      </body>
    </html>
  );
}
