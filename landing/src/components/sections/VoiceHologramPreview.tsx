"use client";

import React, { useState } from "react";
import { 
  Mic, 
  Radio, 
  Volume2, 
  Sparkles, 
  Zap, 
  Bot, 
  Activity, 
  Play,
  Pause,
  CheckCircle2,
  Headphones
} from "lucide-react";

interface VoiceSample {
  command: string;
  response: string;
  agent: string;
  latency: string;
}

export const VoiceHologramPreview: React.FC = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeSampleIndex, setActiveSampleIndex] = useState(0);

  const samples: VoiceSample[] = [
    {
      command: "“COSA, tổng hợp tình hình thực thi OKRs Q3 và các điểm nghẽn nghiêm trọng nhất.”",
      response: "“Dạ thưa anh, hiện có 2 Key Results đang bị chậm tiến độ 14% do thiếu nhân lực phần Frontend. CSO Iris đã phân bổ lại 4 task ưu tiên cao cho tuần tới.”",
      agent: "CSO Iris (Strategy Lead)",
      latency: "240ms",
    },
    {
      command: "“Kích hoạt chiến dịch ra mắt sản phẩm trên Landing Page và thông báo cho đội Sales.”",
      response: "“Đã phát sinh mã Next.js Landing Module, đẩy lên Hostinger VPS thành công và thiết lập 3 luồng webhook gửi thông báo về Zalo nhóm Bán hàng.”",
      agent: "CMO Nova (Growth Lead)",
      latency: "295ms",
    },
    {
      command: "“Kiểm tra dòng tiền dự kiến tháng tới nếu ký thêm 3 hợp đồng Enterprise.”",
      response: "“Dòng tiền ròng sẽ tăng thêm 42,000 USD, Runway của công ty được kéo dài thêm 4.5 tháng. Em đã cập nhật biểu đồ tài chính vào dashboard.”",
      agent: "CFO Apex (Finance Officer)",
      latency: "210ms",
    },
  ];

  return (
    <section id="voice-hub" className="py-24 bg-[#070c18] relative overflow-hidden border-t border-cosa-border">
      {/* Background Holographic Aura */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[650px] bg-cosa-cyan/10 blur-[160px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Visual Holographic Sphere */}
          <div className="lg:col-span-6 flex flex-col items-center justify-center text-center space-y-8">
            <div className="relative flex items-center justify-center w-72 h-72 sm:w-88 sm:h-88">
              {/* Outer Cyber Rings */}
              <div className="absolute inset-0 rounded-full border border-cosa-cyan/20 animate-spin" style={{ animationDuration: "20s" }} />
              <div className="absolute inset-4 rounded-full border border-dashed border-cosa-sky/30 animate-spin" style={{ animationDuration: "12s", animationDirection: "reverse" }} />
              <div className="absolute inset-10 rounded-full border border-cosa-blue/40 animate-pulse" />

              {/* Glowing Hologram Center */}
              <div className="relative w-40 h-40 sm:w-48 sm:h-48 rounded-full bg-gradient-to-tr from-cosa-cyan via-cosa-blue to-purple-600 p-1 shadow-[0_0_80px_rgba(0,240,255,0.6)] flex items-center justify-center">
                <div className="w-full h-full bg-[#04070e] rounded-full flex flex-col items-center justify-center p-4">
                  <Mic className="w-10 h-10 text-cosa-cyan animate-pulse mb-2" />
                  <span className="text-[11px] font-mono uppercase tracking-widest text-cosa-cyan font-bold">
                    LIVEKIT STREAM
                  </span>
                  <span className="text-[10px] text-emerald-400 font-mono mt-0.5">FULL DUPLEX</span>
                </div>
              </div>

              {/* Orbiting Tech Badges */}
              <div className="absolute -top-2 px-3 py-1 rounded-full bg-[#0d172a] border border-cosa-cyan/40 text-[11px] font-mono text-cosa-cyan shadow-lg">
                Opus 48kHz HD Audio
              </div>
              <div className="absolute -bottom-2 px-3 py-1 rounded-full bg-[#0d172a] border border-emerald-500/40 text-[11px] font-mono text-emerald-400 shadow-lg">
                Latency: &lt; 250ms
              </div>
            </div>

            {/* Audio Waveform Bar */}
            <div className="w-full max-w-md bg-[#0d172a] p-4 rounded-2xl border border-cosa-border space-y-2">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                <span className="flex items-center gap-1.5 text-cosa-cyan">
                  <Radio className="w-3.5 h-3.5 animate-pulse" />
                  <span>Realtime Voice Waveform</span>
                </span>
                <span className="text-emerald-400 font-bold">ACTIVE STREAMING</span>
              </div>
              <div className="flex items-center justify-center gap-1.5 h-12 pt-1">
                {[30, 60, 90, 45, 100, 75, 40, 85, 95, 60, 30, 80, 100, 70, 50, 90, 60, 40, 85, 30].map((h, i) => (
                  <div
                    key={i}
                    className="w-1.5 bg-gradient-to-t from-cosa-blue via-cosa-cyan to-white rounded-full animate-pulse"
                    style={{
                      height: `${h}%`,
                      animationDuration: "1s",
                      animationDelay: `${i * 0.05}s`,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Description & Interactive Audio Samples */}
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cosa-sky/10 border border-cosa-sky/30 text-cosa-sky text-xs font-mono">
              <Headphones className="w-3.5 h-3.5" />
              <span>VOICE-FIRST OPERATING SYSTEM</span>
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-[1.3] sm:leading-[1.25] pb-2">
              Đàm Thoại Tự Nhiên &{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cosa-cyan to-cosa-sky inline-block pt-1">
                Điều Khiển Toàn Bộ Doanh Nghiệp
              </span>
            </h2>

            <p className="text-slate-300 text-base leading-relaxed">
              Không cần gõ phím hay chuyển đổi giữa hàng chục ứng dụng. Bạn chỉ cần trò chuyện tự nhiên với COSA OS như một người trợ lý điều hành cấp cao.
            </p>

            {/* Interactive Sample Cards */}
            <div className="space-y-3 pt-2">
              {samples.map((sample, idx) => {
                const isActive = activeSampleIndex === idx;
                return (
                  <div
                    key={idx}
                    onClick={() => setActiveSampleIndex(idx)}
                    className={`p-4 rounded-2xl cursor-pointer transition-all ${
                      isActive
                        ? "bg-[#0d172a] border-2 border-cosa-cyan shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                        : "bg-[#080f1e] border border-cosa-border hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-1.5 font-mono">
                      <span className="text-cosa-cyan font-bold">{sample.agent}</span>
                      <span className="text-emerald-400">Độ trễ: {sample.latency}</span>
                    </div>
                    <div className="text-xs sm:text-sm text-slate-200 font-medium mb-2">
                      🗣️ {sample.command}
                    </div>
                    {isActive && (
                      <div className="p-3 rounded-xl bg-[#04070e] border border-slate-800 text-xs text-cosa-sky leading-relaxed">
                        🤖 {sample.response}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
