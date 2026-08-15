"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Terminal, 
  Cpu, 
  Sparkles, 
  ShieldCheck, 
  Menu, 
  X, 
  ArrowRight, 
  Zap,
  Activity,
  Layers
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
    { name: "Tính năng", href: "#features" },
    { name: "AI Agent", href: "#playground" },
    { name: "Giọng nói AI", href: "#voice-hub" },
    { name: "Tính ROI", href: "#roi-calculator" },
    { name: "Bảo mật", href: "#architecture" },
    { name: "Bảng giá", href: "#pricing" },
    { name: "FAQ", href: "#faq" },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#070c18]/85 backdrop-blur-xl border-b border-cosa-border shadow-[0_10px_30px_-10px_rgba(0,0,0,0.8)] py-3"
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
            <span className="font-bold text-xl tracking-wider text-white group-hover:text-cosa-cyan transition-colors">
              COSA<span className="text-cosa-cyan">.OS</span>
            </span>
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
          <div className="hidden md:flex items-center gap-4">
            <button
              onClick={() => onOpenLeadModal("navbar_cta")}
              className="relative inline-flex items-center justify-center p-0.5 overflow-hidden text-sm font-semibold rounded-xl group bg-gradient-to-br from-cosa-cyan to-cosa-blue text-white shadow-[0_0_20px_rgba(0,240,255,0.25)] hover:shadow-[0_0_30px_rgba(0,240,255,0.5)] transition-all transform active:scale-95"
            >
              <span className="relative px-4 py-2 transition-all ease-in duration-200 bg-[#070c18] rounded-[10px] group-hover:bg-transparent flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cosa-cyan group-hover:text-white" />
                <span>Đặt Lịch Demo</span>
                <ArrowRight className="w-4 h-4 text-cosa-cyan group-hover:text-white group-hover:translate-x-0.5 transition-transform" />
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
          <div className="md:hidden mt-4 p-4 rounded-2xl bg-[#0d172a]/95 border border-cosa-border backdrop-blur-2xl space-y-3">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="block text-sm font-medium text-slate-300 hover:text-cosa-cyan py-2 px-3 rounded-lg hover:bg-white/5 transition-all"
              >
                {link.name}
              </a>
            ))}
            <div className="pt-2 border-t border-cosa-border">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onOpenLeadModal("mobile_menu");
                }}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-cosa-cyan to-cosa-blue text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg"
              >
                <Sparkles className="w-4 h-4" />
                <span>Đặt Lịch Demo & Tư Vấn</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
