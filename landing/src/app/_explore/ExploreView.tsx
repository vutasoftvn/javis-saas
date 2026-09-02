"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { HeroSection } from "@/components/sections/HeroSection";
import { SocialProofBar } from "@/components/sections/SocialProofBar";
import { LivePlayground } from "@/components/sections/LivePlayground";
import { BentoFeatures } from "@/components/sections/BentoFeatures";
import { VoiceHologramPreview } from "@/components/sections/VoiceHologramPreview";
import { RoiCalculator } from "@/components/sections/RoiCalculator";
import { SecurityArchitecture } from "@/components/sections/SecurityArchitecture";
import { PricingSection } from "@/components/sections/PricingSection";
import { TestimonialsSection } from "@/components/sections/TestimonialsSection";
import { FaqSection } from "@/components/sections/FaqSection";
import { LeadFormSection } from "@/components/sections/LeadFormSection";
import { Footer } from "@/components/layout/Footer";
import { LeadCaptureModal } from "@/components/sections/LeadCaptureModal";

export default function ExplorePage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [modalSource, setModalSource] = useState("direct");

  const handleOpenModal = (source: string = "direct") => {
    setModalSource(source);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
  };

  return (
    <main className="min-h-screen bg-[#070c18] text-white flex flex-col selection:bg-cosa-cyan selection:text-slate-950">
      {/* Top Banner: Return to Intro / Countdown */}
      <div className="w-full bg-slate-950/90 border-b border-cyan-500/20 py-2 px-4 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs font-mono">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 font-bold tracking-wide transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>← Quay lại Trang Intro & Bộ Đếm Ngược 01/01/2027</span>
          </Link>
          <span className="text-slate-400 font-mono">
            Hotline Hỗ Trợ: <a href="tel:+84888248257" className="text-cyan-300 font-bold hover:underline">(+84) 888-248-257</a>
          </span>
        </div>
      </div>

      {/* Sticky Navigation Bar */}
      <Navbar onOpenLeadModal={handleOpenModal} />

      {/* Hero Section with Hologram Terminal */}
      <HeroSection onOpenLeadModal={handleOpenModal} />

      {/* Social Proof & Tech Ecosystem Bar */}
      <SocialProofBar />

      {/* Live Interactive Scenario Playground */}
      <LivePlayground onOpenLeadModal={handleOpenModal} />

      {/* 5 Core Architectural Pillars (Bento Grid) */}
      <BentoFeatures />

      {/* Bot Enterprise & 3D Hologram Hub */}
      <VoiceHologramPreview />

      {/* Interactive ROI & Operational Savings Calculator */}
      <RoiCalculator onOpenLeadModal={handleOpenModal} />

      {/* Enterprise Security, Snowflake ID & On-Premise Architecture */}
      <SecurityArchitecture />

      {/* Transparent Pricing Packages */}
      <PricingSection onOpenLeadModal={handleOpenModal} />

      {/* Customer Success Stories & Testimonials */}
      <TestimonialsSection />

      {/* Frequently Asked Questions */}
      <FaqSection />

      {/* Main Lead Generation & Early Access Onboarding Form */}
      <LeadFormSection onSuccess={() => {}} />

      {/* Footer */}
      <Footer />

      {/* Pop-up Lead Capture Modal for fast action clicks */}
      <LeadCaptureModal
        isOpen={modalOpen}
        onClose={handleCloseModal}
        initialSource={modalSource}
      />
    </main>
  );
}
