"use client";

import React from "react";
import { X } from "lucide-react";
import { EarlyAccessForm } from "../forms/EarlyAccessForm";

interface LeadCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialSource?: string;
}

export const LeadCaptureModal: React.FC<LeadCaptureModalProps> = ({
  isOpen,
  onClose,
  initialSource = "general_cta",
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn overflow-y-auto">
      <div className="relative w-full max-w-xl my-8 rounded-3xl bg-[#080f1e] border border-cosa-cyan/40 p-6 sm:p-8 shadow-[0_0_60px_rgba(0,240,255,0.25)] max-h-[90vh] overflow-y-auto">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full bg-[#0d172a] text-slate-400 hover:text-white border border-slate-700 hover:border-cosa-cyan transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="pt-1">
          <EarlyAccessForm
            variant="modal"
            initialSource={initialSource}
            onClose={onClose}
          />
        </div>
      </div>
    </div>
  );
};


