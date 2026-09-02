"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, Cpu, Users, Target } from "lucide-react";
import { CountdownTimer } from "@/components/sections/CountdownTimer";
import { IntroContactBar } from "@/components/sections/IntroContactBar";
import { IntroFeaturesMatrix } from "@/components/sections/IntroFeaturesMatrix";

export default function IntroHome() {
  return (
    <main className="min-h-screen bg-[#070c18] text-white flex flex-col selection:bg-cyan-400 selection:text-slate-950 relative overflow-x-hidden">
      {/* Ambient background glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[450px] bg-gradient-to-b from-cyan-500/15 via-blue-600/10 to-transparent blur-[120px] pointer-events-none -z-10" />
      <div className="absolute top-[800px] right-0 w-[500px] h-[500px] bg-cyan-600/10 blur-[150px] pointer-events-none -z-10" />
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-600/10 blur-[150px] pointer-events-none -z-10" />

      {/* Cyberpunk Top Grid Overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none -z-10"
        style={{
          backgroundImage:
            "linear-gradient(to right, #00f0ff 1px, transparent 1px), linear-gradient(to bottom, #00f0ff 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Header / Mini Navbar */}
      <header className="w-full border-b border-cyan-500/15 bg-slate-950/70 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 sm:h-20 flex items-center justify-between">
          {/* Brand Logo */}
          <Link href="/" className="flex items-center gap-2.5 sm:gap-3 group">
            <div className="relative flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-[#00f0ff] to-[#0072ff] p-[1px] shadow-[0_0_20px_rgba(0,240,255,0.4)] group-hover:shadow-[0_0_25px_rgba(0,240,255,0.7)] transition-all shrink-0">
              <div className="w-full h-full bg-[#04070e] rounded-[11px] flex items-center justify-center">
                <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div className="flex flex-col whitespace-nowrap">
              <span className="font-extrabold text-base sm:text-lg tracking-wider text-white group-hover:text-cyan-400 transition-colors flex items-center">
                COSA <span className="text-cyan-400 ml-1">OS</span>
              </span>
              <span className="text-[9px] sm:text-[10px] text-slate-400 font-mono tracking-tight hidden sm:block">
                Create · Operate · Scale · Automate
              </span>
            </div>
          </Link>

          {/* Right Status & Quick Action */}
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="hidden sm:inline-flex items-center gap-1.5 text-xs font-mono text-slate-300 bg-slate-900/90 px-3.5 py-1.5 rounded-full border border-cyan-500/30 shadow-[0_0_15px_rgba(0,240,255,0.1)]">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span>Đăng Ký Sớm: <strong className="text-cyan-400">Còn 42 Suất</strong></span>
            </div>

            <a
              href="#early-access-form"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 text-xs sm:text-sm font-bold font-mono transition-all duration-200 shadow-[0_0_15px_rgba(0,240,255,0.15)] group"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Đăng Ký Sớm</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Hero Intro Content */}
      <section className="pt-12 sm:pt-20 pb-8 px-4 sm:px-6 lg:px-8 text-center max-w-7xl mx-auto w-full">
        <div className="w-full mx-auto">
          {/* Main Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight flex flex-col items-center gap-1 sm:gap-2 pb-1 max-w-4xl mx-auto"
          >
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue neon-text-glow inline-block py-1 leading-tight">
              HỆ ĐIỀU HÀNH DOANH NGHIỆP AI
            </span>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan via-cosa-sky to-cosa-blue neon-text-glow inline-block py-1 leading-tight">
              &amp; MÔ HÌNH OPC
            </span>
          </motion.h1>

          {/* 3 Core Highlight Cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6 w-full mx-auto pt-8 pb-4 text-left"
          >
            {/* Card 1: Hợp nhất nhân sự */}
            <div className="p-5 sm:p-6 rounded-2xl bg-[#080f1e]/90 border border-cosa-cyan/30 hover:border-cosa-cyan/70 transition-all shadow-[0_0_25px_rgba(0,240,255,0.08)] group h-full flex flex-col justify-start backdrop-blur-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-cosa-cyan/15 border border-cosa-cyan/30 flex items-center justify-center text-cosa-cyan group-hover:scale-105 transition-transform shrink-0">
                  <Users className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <span className="text-xs font-mono uppercase text-cyan-400 tracking-wider">Trụ Cột Nhân Sự</span>
                  <h3 className="text-base font-bold text-white">Hợp Nhất AI &amp; Người Thật</h3>
                </div>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed text-justify">
                Hợp nhất <strong className="text-white">Lực lượng Lao động AI &amp; Người thật</strong> trong một cơ cấu tổ chức duy nhất, tối ưu cho mô hình <strong className="text-cyan-400">OPC (Doanh nghiệp một người)</strong> và startup tăng trưởng.
              </p>
            </div>

            {/* Card 2: Vận hành 12 tuần & TT58 */}
            <div className="p-5 sm:p-6 rounded-2xl bg-[#080f1e]/90 border border-cosa-violet/30 hover:border-cosa-violet/70 transition-all shadow-[0_0_25px_rgba(139,92,246,0.08)] group h-full flex flex-col justify-start backdrop-blur-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-cosa-violet/15 border border-cosa-violet/30 flex items-center justify-center text-cosa-violet group-hover:scale-105 transition-transform shrink-0">
                  <Target className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <span className="text-xs font-mono uppercase text-violet-400 tracking-wider">Trụ Cột Vận Hành</span>
                  <h3 className="text-base font-bold text-white">Vận Hành 12 Tuần &amp; TT 58</h3>
                </div>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed text-justify">
                Vận hành chu kỳ chiến lược <strong className="text-white">12-Week Year &amp; OKRs</strong>, quản trị dòng tiền <strong className="text-white">Thông tư 58/TT-BTC</strong> với chốt chặn phê duyệt tài chính tức thời.
              </p>
            </div>

            {/* Card 3: Miễn phí phân tích */}
            <div className="p-5 sm:p-6 rounded-2xl bg-[#080f1e]/90 border border-cosa-emerald/40 hover:border-cosa-emerald/80 transition-all shadow-[0_0_25px_rgba(16,185,129,0.12)] group h-full flex flex-col justify-start backdrop-blur-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-cosa-emerald/15 border border-cosa-emerald/30 flex items-center justify-center text-cosa-emerald group-hover:scale-105 transition-transform shrink-0">
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <span className="text-xs font-mono uppercase text-emerald-400 tracking-wider font-bold">Miễn Phí 100% (0đ)</span>
                  <h3 className="text-base font-bold text-white">Miễn Phí Phân Tích Dự Án</h3>
                </div>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed text-justify">
                <strong className="text-emerald-400">Miễn phí 100%</strong> cho giai đoạn phân tích dự án, nghiên cứu chân dung người dùng (User Persona) và lập kế hoạch PRD cho mô hình OPC.
              </p>
            </div>
          </motion.div>
        </div>

        {/* Countdown Timer Section */}
        <CountdownTimer />
      </section>

      {/* Core Capabilities Matrix */}
      <section className="py-8 bg-gradient-to-b from-transparent via-slate-950/60 to-transparent border-t border-b border-slate-800/60">
        <IntroFeaturesMatrix />
      </section>

      {/* Multi-channel Contact Bar (Bottom) */}
      <section className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        <IntroContactBar />
      </section>

      {/* Simplified Footer with MIVA Corp Ownership */}
      <footer className="w-full border-t border-slate-800/80 bg-slate-950/90 py-8 px-4 sm:px-6 lg:px-8 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-400 font-mono">
          <div className="flex flex-col sm:flex-row items-center gap-2 text-center sm:text-left">
            <span className="font-bold text-white tracking-wider">MIVA Corp</span>
            <span className="hidden sm:inline">·</span>
            <span>Copyright © 2026-2027 <strong className="text-cyan-300 font-normal">MIVA Corp</strong></span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-slate-300">
            <a href="mailto:mivacorp.vn@gmail.com" className="hover:text-cyan-300 transition-colors flex items-center gap-1.5">
              <span>Email:</span>
              <strong className="text-cyan-300 font-normal">mivacorp.vn@gmail.com</strong>
            </a>
            <span className="hidden sm:inline text-slate-600">|</span>
            <a href="tel:+84888248257" className="hover:text-cyan-300 transition-colors flex items-center gap-1.5">
              <span>Hotline:</span>
              <strong className="text-cyan-300 font-normal">(+84) 888-248-257</strong>
            </a>
          </div>

          <div className="text-slate-500 text-center md:text-right">
            All rights reserved. Sẵn sàng phát hành 01/01/2027.
          </div>
        </div>
      </footer>
    </main>
  );
}
