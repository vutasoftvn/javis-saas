"use client";

import React, { useState, useEffect } from "react";
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
    { name: "Tính Năng", href: "#features" },
    { name: "AI Workforce", href: "#playground" },
    { name: "Trợ Lý AI", href: "#ai-assistant" },
    { name: "Tính ROI", href: "#roi-calculator" },
    { name: "Bảo Mật", href: "#architecture" },
    { name: "Bảng Giá", href: "#pricing" },
    { name: "FAQ", href: "#faq" },
  ];

  const handleScrollToTop = (e: React.MouseEvent) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#070c18]/90 backdrop-blur-xl border-b border-cosa-border shadow-[0_10px_30px_-10px_rgba(0,0,0,0.8)] py-3"
          : "bg-transparent py-4 sm:py-5"
      }`}
    >
      <div className="w-full max-w-[1680px] mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-2 xl:gap-4">
          {/* Logo Brand - Scroll to top on click */}
          <a
            href="#"
            onClick={handleScrollToTop}
            className="flex items-center gap-2.5 sm:gap-3 group shrink-0 cursor-pointer"
            title="Cuộn về đầu trang"
          >
            <div className="relative flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-[#00f0ff] to-[#0072ff] p-[1px] shadow-[0_0_20px_rgba(0,240,255,0.4)] group-hover:shadow-[0_0_25px_rgba(0,240,255,0.7)] transition-all shrink-0">
              <div className="w-full h-full bg-[#04070e] rounded-[11px] flex items-center justify-center">
                <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-cosa-cyan animate-pulse" />
              </div>
            </div>
            <div className="flex flex-col whitespace-nowrap">
              <span className="font-extrabold text-base sm:text-lg tracking-wider text-white group-hover:text-cosa-cyan transition-colors flex items-center">
                COSA <span className="text-cosa-cyan ml-1">OS</span>
              </span>
              <span className="text-[9px] sm:text-[10px] text-slate-400 font-medium tracking-tight hidden sm:block">
                Hệ Điều Hành Doanh Nghiệp AI
              </span>
            </div>
          </a>

          {/* Desktop Nav Items - Strictly 1 Line */}
          <nav className="hidden lg:flex items-center gap-3 xl:gap-5 2xl:gap-7 shrink-0">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-xs xl:text-sm font-medium text-slate-300 hover:text-cosa-cyan transition-colors relative py-1 whitespace-nowrap"
              >
                {link.name}
              </a>
            ))}
          </nav>

          {/* Right Action & Status */}
          <div className="hidden md:flex items-center gap-2 xl:gap-3 shrink-0">
            <div className="hidden xl:flex items-center gap-1.5 text-[11px] font-mono text-slate-400 bg-[#0d172a] px-3 py-1.5 rounded-full border border-cosa-border whitespace-nowrap">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span>Early Access: <strong className="text-cosa-cyan">Còn 42 Suất</strong></span>
            </div>

            <button
              onClick={() => onOpenLeadModal("navbar_cta")}
              className="relative inline-flex items-center justify-center p-0.5 overflow-hidden text-xs font-bold rounded-xl group bg-gradient-to-br from-cosa-cyan via-cosa-sky to-cosa-blue text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.3)] hover:shadow-[0_0_30px_rgba(0,240,255,0.6)] transition-all transform active:scale-95 shrink-0"
            >
              <span className="relative px-3.5 py-2 sm:px-4 sm:py-2.5 transition-all ease-in duration-200 bg-gradient-to-r from-cosa-cyan to-cosa-sky rounded-[10px] flex items-center gap-1.5 sm:gap-2 text-slate-950 whitespace-nowrap">
                <Sparkles className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-950 shrink-0" />
                <span>Đăng Ký Sớm</span>
                <ArrowRight className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-950 group-hover:translate-x-0.5 transition-transform shrink-0" />
              </span>
            </button>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex lg:hidden items-center gap-2">
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
                  className="text-sm font-medium text-slate-200 hover:text-cosa-cyan transition-colors py-1.5 whitespace-nowrap"
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
