import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "COSA OS — Hệ Điều Hành Doanh Nghiệp AI Tự Trị Cho Nhà Sáng Lập",
  description:
    "Hệ điều hành doanh nghiệp AI thế hệ mới: Hợp nhất nhân sự Người thật & AI Agents (WorkforceMember), điều hành chu kỳ chiến lược 12-Week Year & OKRs, kiểm soát dòng tiền kế toán TT88/TT58, tương tác Giọng nói LiveKit Realtime và bảo mật On-Premise.",
  keywords: [
    "COSA OS",
    "Hệ điều hành doanh nghiệp AI",
    "Unified Workforce",
    "WorkforceMember",
    "12-Week Year",
    "OKRs AI",
    "Kế toán Thông tư 88",
    "LiveKit Realtime Voice",
    "PostgreSQL Local Data Plane",
    "Early Access Waitlist",
  ],
  authors: [{ name: "COSA OS Intelligence Team" }],
  openGraph: {
    title: "COSA OS — The AI Operating System for Startups & Founders",
    description:
      "Tự trị hóa vận hành doanh nghiệp với đội ngũ Chuyên viên AI hợp nhất, quản trị chiến lược 12 tuần, kế toán TT88 và Trợ lý Giọng nói Realtime LiveKit.",
    type: "website",
    locale: "vi_VN",
  },
  twitter: {
    card: "summary_large_image",
    title: "COSA OS — Autonomous Company AI Platform",
    description:
      "Hệ điều hành doanh nghiệp AI tự trị đầu tiên tại Việt Nam với LiveKit Voice, pgvector RAG và kế toán Thông tư 88.",
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
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased bg-[#070c18] text-white selection:bg-[#00f0ff] selection:text-[#04070e]`}
      >
        {children}
      </body>
    </html>
  );
}
