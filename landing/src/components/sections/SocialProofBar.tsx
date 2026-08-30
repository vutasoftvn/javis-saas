import React from "react";
import { Sparkles } from "lucide-react";

export const SocialProofBar: React.FC = () => {
  const techStack = [
    { name: "COSA AI Voice & Chat", tag: "Realtime Assistant" },
    { name: "PostgreSQL Local", tag: "Data Plane & pgvector" },
    { name: "Encore.ts Microservices", tag: "Event-driven Backend" },
    { name: "Flutter Desktop", tag: "macOS / Windows Native" },
    { name: "Resend Email API", tag: "Transactional Comms" },
    { name: "DeepSeek V3 / R1", tag: "Reasoning & Coding" },
    { name: "MinIO Private S3", tag: "Secure Document Vault" },
  ];

  return (
    <section className="py-8 border-y border-cosa-border/60 bg-[#04070e]/80 backdrop-blur-md relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Label */}
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 shrink-0 uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-cosa-cyan" />
            <span>Hạ Tầng Công Nghệ Tiên Tiến</span>
          </div>

          {/* Tech Grid */}
          <div className="flex flex-wrap items-center justify-center md:justify-end gap-2.5 sm:gap-3">
            {techStack.map((p, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0d172a]/70 border border-cosa-border hover:border-cosa-cyan/40 transition-all group"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-cosa-cyan/50 group-hover:bg-cosa-cyan transition-colors" />
                <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors">
                  {p.name}
                </span>
                <span className="text-[10px] text-slate-500 hidden xl:inline-block font-mono">
                  ({p.tag})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
