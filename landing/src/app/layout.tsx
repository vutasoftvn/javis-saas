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
  title: "COSA OS 13.2 — Hệ Điều Hành Doanh Nghiệp Tự Trị AI Đa Tác Vụ",
  description:
    "Nền tảng vận hành doanh nghiệp tự trị bằng AI hàng đầu: Tích hợp 7 AI Agents chuyên trách, Hoạch định chiến lược OKRs, Trợ lý giọng nói LiveKit Realtime, Kho tri thức Enterprise Vault RAG và CRM Bán hàng tự động.",
  keywords: [
    "COSA OS",
    "Javis SaaS",
    "Autonomous Enterprise",
    "AI Workforce",
    "Doanh nghiệp tự trị",
    "OKRs AI",
    "Realtime Voice LiveKit",
    "pgvector RAG",
    "Hostinger VPS MCP",
    "Next.js Landing",
  ],
  authors: [{ name: "COSA Intelligence Team" }],
  openGraph: {
    title: "COSA OS 13.2 — Autonomous Company AI Operating System",
    description:
      "Tự động hóa toàn diện chiến lược, kinh doanh, tiếp thị và vận hành với đội ngũ 7 AI Agents chuyên trách.",
    type: "website",
    locale: "vi_VN",
  },
  twitter: {
    card: "summary_large_image",
    title: "COSA OS 13.2 — Autonomous AI Workforce Platform",
    description:
      "Hệ điều hành doanh nghiệp tự trị bằng AI thế hệ mới với LiveKit Realtime Voice & pgvector RAG.",
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
