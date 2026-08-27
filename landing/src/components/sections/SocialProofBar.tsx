import React from "react";
import { Sparkles } from "lucide-react";

export const SocialProofBar: React.FC = () => {
  const partners = [
    { name: "LiveKit Realtime", tag: "Ultra Low Latency Voice" },
    { name: "PostgreSQL pgvector", tag: "Enterprise RAG & Memory" },
    { name: "Hostinger API MCP", tag: "Programmable VPS Deploy" },
    { name: "MinIO Private S3", tag: "Secure Document Vault" },
    { name: "DeepSeek V3 / R1", tag: "High-Reasoning Models" },
    { name: "OpenRouter Gateway", tag: "Multi-Model AI Mesh" },
    { name: "DSPy Framework", tag: "MIPROv2 Prompt Optimizer" },
  ];

  return (
    <section className="py-10 border-y border-cosa-border/60 bg-[#04070e]/80 backdrop-blur-md relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Label */}
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 shrink-0 uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-cosa-cyan" />
            <span>Tương thích & Tích hợp sâu</span>
          </div>

          {/* Partner Tech Grid */}
          <div className="flex flex-wrap items-center justify-center md:justify-end gap-3 sm:gap-4">
            {partners.map((p, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0d172a]/70 border border-cosa-border hover:border-cosa-cyan/40 transition-all group"
              >
                <div className="w-2 h-2 rounded-full bg-cosa-cyan/50 group-hover:bg-cosa-cyan transition-colors" />
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
