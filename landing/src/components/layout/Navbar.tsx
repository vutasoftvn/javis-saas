"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Cpu,
  Sparkles,
  Menu,
  X,
  ArrowRight,
} from "lucide-react";

interface NavbarProps {
  onOpenLeadModal: (source?: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenLeadModal }) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Trụ Cột Cốt Lõi", href: "#features" },
    { name: "AI Workforce", href: "#playground" },
    { name: "Giọng Nói LiveKit", href: "#voice-hub" },
    { name: "Tính ROI", href: "#roi-calculator" },
    { name: "Bảo Mật On-Premise", href: "#architecture" },
    { name: "Bảng Giá", href: "#pricing" },
    { name: "FAQ", href: "#faq" },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#070c18]/90 backdrop-blur-xl border-b border-cosa-border shadow-[0_10px_30px_-10px_rgba(0,0,0,0.8)] py-3"
          : "bg-transparent py-5"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          {/* Logo Brand */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-[#00f0ff] to-[#0072ff] p-[1px] shadow-[0_0_20px_rgba(0,240,255,0.4)] group-hover:shadow-[0_0_25px_rgba(0,240,255,0.7)] transition-all">
              <div className="w-full h-full bg-[#04070e] rounded-[11px] flex items-center justify-center">
                <Cpu className="w-5 h-5 text-cosa-cyan animate-pulse" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-lg tracking-wider text-white group-hover:text-cosa-cyan transition-colors flex items-center gap-1.5">
                COSA <span className="text-cosa-cyan">OS</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cosa-cyan/15 text-cosa-cyan border border-cosa-cyan/30 ml-1">ENTERPRISE</span>
              </span>
              <span className="text-[10px] text-slate-400 font-medium tracking-tight">
                Hệ Điều Hành Doanh Nghiệp AI
              </span>
            </div>
          </Link>

          {/* Desktop Nav Items */}
          <nav className="hidden lg:flex items-center gap-6">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-sm font-medium text-slate-300 hover:text-cosa-cyan transition-colors relative py-1"
              >
                {link.name}
              </a>
            ))}
          </nav>

          {/* Right Action & Status */}
          <div className="hidden md:flex items-center gap-3">
            <div className="hidden xl:flex items-center gap-1.5 text-[11px] font-mono text-slate-400 bg-[#0d172a] px-3 py-1.5 rounded-full border border-cosa-border">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Early Access: <strong className="text-cosa-cyan">Còn 42 Suất</strong></span>
            </div>

            <button
              onClick={() => onOpenLeadModal("navbar_cta")}
              className="relative inline-flex items-center justify-center p-0.5 overflow-hidden text-xs font-bold rounded-xl group bg-gradient-to-br from-cosa-cyan via-cosa-sky to-cosa-blue text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.3)] hover:shadow-[0_0_30px_rgba(0,240,255,0.6)] transition-all transform active:scale-95"
            >
              <span className="relative px-4 py-2.5 transition-all ease-in duration-200 bg-gradient-to-r from-cosa-cyan to-cosa-sky rounded-[10px] flex items-center gap-2 text-slate-950">
                <Sparkles className="w-4 h-4 text-slate-950" />
                <span>Đăng Ký Dùng Sớm</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-950 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </button>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-[#0d172a] text-slate-300 hover:text-cosa-cyan border border-cosa-border focus:outline-none"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown */}
        {mobileMenuOpen && (
          <div className="lg:hidden mt-4 p-5 rounded-2xl bg-[#080f1e]/95 border border-cosa-border backdrop-blur-2xl shadow-2xl space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs font-mono text-slate-400">
              <span>Đợt Đăng Ký Sớm #1</span>
              <span className="text-cosa-cyan font-bold">Còn 42/100 suất</span>
            </div>

            <div className="flex flex-col space-y-2.5">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-sm font-medium text-slate-200 hover:text-cosa-cyan transition-colors py-1.5"
                >
                  {link.name}
                </a>
              ))}
            </div>

            <div className="pt-2 border-t border-slate-800 flex flex-col gap-2">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onOpenLeadModal("mobile_menu_cta");
                }}
                className="w-full py-3 rounded-xl font-bold text-xs text-slate-950 bg-gradient-to-r from-cosa-cyan to-cosa-sky shadow-[0_0_20px_rgba(0,240,255,0.4)] flex items-center justify-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                <span>Nhận Thẻ Early Access VIP</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
