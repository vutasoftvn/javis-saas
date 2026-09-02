"use client";

import React from "react";
import { motion } from "framer-motion";
import { Phone, Send } from "lucide-react";

// Logo Zalo Vector Chuẩn
const ZaloIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 48 48" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
    <path
      d="M24 4C12.954 4 4 12.507 4 23C4 28.79 6.776 33.957 11.168 37.456L8.5 44.5L16.294 42.112C18.666 43.328 21.264 44 24 44C35.046 44 44 35.493 44 25C44 14.507 35.046 4 24 4Z"
      fill="currentColor"
      fillOpacity="0.2"
    />
    <path
      d="M24 4C12.954 4 4 12.507 4 23C4 28.79 6.776 33.957 11.168 37.456L8.5 44.5L16.294 42.112C18.666 43.328 21.264 44 24 44C35.046 44 44 35.493 44 25C44 14.507 35.046 4 24 4Z"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <text
      x="50%"
      y="57%"
      dominantBaseline="middle"
      textAnchor="middle"
      fill="currentColor"
      fontSize="13"
      fontWeight="900"
      fontFamily="system-ui, -apple-system, sans-serif"
      letterSpacing="-0.5px"
    >
      Zalo
    </text>
  </svg>
);

// Logo WhatsApp Vector Chuẩn
const WhatsAppIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
    <path
      d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M10 9.5c0 .8.7 1.5 1.5 1.5h1c.8 0 1.5.7 1.5 1.5v1c0 .8-.7 1.5-1.5 1.5"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
);

import { EmailSubscribeForm } from "./EmailSubscribeForm";

export function IntroContactBar() {
  const rawPhoneNumber = "+84888248257";
  const zaloNumber = "84888248257";

  const contactChannels = [
    {
      name: "Điện Thoại",
      icon: Phone,
      href: `tel:${rawPhoneNumber}`,
      color: "from-cyan-500 to-blue-600",
      border: "border-cyan-500/40",
      bgHover: "hover:border-cyan-400 hover:shadow-[0_0_20px_rgba(0,240,255,0.3)]",
    },
    {
      name: "Zalo",
      icon: ZaloIcon,
      href: `https://zalo.me/${zaloNumber}`,
      color: "from-blue-500 to-indigo-600",
      border: "border-blue-500/40",
      bgHover: "hover:border-blue-400 hover:shadow-[0_0_20px_rgba(59,130,246,0.3)]",
    },
    {
      name: "WhatsApp",
      icon: WhatsAppIcon,
      href: `https://wa.me/${zaloNumber}`,
      color: "from-emerald-500 to-teal-600",
      border: "border-emerald-500/40",
      bgHover: "hover:border-emerald-400 hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]",
    },
    {
      name: "Telegram",
      icon: Send,
      href: `https://t.me/+84888248257`,
      color: "from-sky-400 to-blue-500",
      border: "border-sky-400/40",
      bgHover: "hover:border-sky-400 hover:shadow-[0_0_20px_rgba(56,189,248,0.3)]",
    },
  ];

  return (
    <div id="early-access-form" className="w-full max-w-7xl mx-auto my-0 px-0 scroll-mt-28">
      <div className="relative rounded-2xl bg-gradient-to-r from-slate-900/90 via-[#0b1329]/90 to-slate-900/90 border border-slate-800 p-6 sm:p-8 backdrop-blur-xl shadow-2xl overflow-hidden">
        {/* Ambient Glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
          {/* Left: Title, Subtitle & Email Form */}
          <div className="text-center lg:text-left w-full lg:max-w-xl xl:max-w-2xl">
            <h3 className="text-xl sm:text-2xl font-extrabold text-white tracking-wider uppercase font-sans">
              TƯ VẤN &amp; ĐẶT LỊCH SỚM
            </h3>
            <p className="text-xs sm:text-sm text-slate-300 mt-1">
              Kết nối trực tiếp với đội ngũ phát triển <span className="text-cyan-400 font-semibold">COSA OS</span>
            </p>

            {/* Embedded Email Form (Compact textfield) */}
            <EmailSubscribeForm className="w-full max-w-md mx-auto lg:mx-0 mt-4" placeholder="Nhập email..." />
          </div>

          {/* Right: 4 Contact Action Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full lg:w-auto shrink-0">
            {contactChannels.map((ch) => {
              const Icon = ch.icon;
              return (
                <motion.a
                  key={ch.name}
                  href={ch.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`flex flex-col items-center justify-center p-4 sm:p-5 rounded-2xl bg-slate-900/80 border ${ch.border} ${ch.bgHover} transition-all duration-300 group min-w-[110px]`}
                >
                  <div className={`p-2.5 rounded-xl bg-gradient-to-br ${ch.color} text-white shadow-md group-hover:scale-110 transition-transform mb-2 flex items-center justify-center`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                    {ch.name}
                  </span>
                </motion.a>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
