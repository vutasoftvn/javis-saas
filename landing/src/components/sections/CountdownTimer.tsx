"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Clock, Sparkles } from "lucide-react";

interface TimeLeft {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalSeconds: number;
}

const TARGET_DATE = new Date("2027-01-01T00:00:00+07:00").getTime();

function calculateTimeLeft(): TimeLeft {
  const now = new Date().getTime();
  const diff = Math.max(0, TARGET_DATE - now);

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
  const minutes = Math.floor((diff / 1000 / 60) % 60);
  const seconds = Math.floor((diff / 1000) % 60);

  return {
    days,
    hours,
    minutes,
    seconds,
    totalSeconds: Math.floor(diff / 1000),
  };
}

export function CountdownTimer() {
  const [mounted, setMounted] = useState(false);
  const [timeLeft, setTimeLeft] = useState<TimeLeft>({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
    totalSeconds: 0,
  });

  useEffect(() => {
    setMounted(true);
    setTimeLeft(calculateTimeLeft());

    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const timeUnits = [
    { labelVi: "NGÀY", value: timeLeft.days, pad: 3 },
    { labelVi: "GIỜ", value: timeLeft.hours, pad: 2 },
    { labelVi: "PHÚT", value: timeLeft.minutes, pad: 2 },
    { labelVi: "GIÂY", value: timeLeft.seconds, pad: 2 },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto my-8 px-0">
      {/* HUD Header Status */}
      <div className="flex items-center justify-center gap-3 mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 text-xs font-mono tracking-widest uppercase backdrop-blur-md shadow-[0_0_20px_rgba(0,240,255,0.15)]">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>ĐẾM NGƯỢC NGÀY PHÁT HÀNH CHÍNH THỨC · 01/01/2027 (GMT+7)</span>
        </div>
      </div>

      {/* Countdown Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-6">
        {timeUnits.map((unit, idx) => {
          const displayValue = mounted
            ? String(unit.value).padStart(unit.pad, "0")
            : "--";

          return (
            <motion.div
              key={unit.labelVi}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1, duration: 0.4 }}
              className="relative group"
            >
              {/* Card Container */}
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900/90 via-slate-950/90 to-[#070c18] border border-cyan-500/20 p-5 sm:p-7 text-center backdrop-blur-xl shadow-2xl transition-all duration-300 group-hover:border-cyan-400/50 group-hover:shadow-[0_0_30px_rgba(0,240,255,0.2)]">
                {/* Tech Grid Background pattern */}
                <div
                  className="absolute inset-0 opacity-[0.04] pointer-events-none"
                  style={{
                    backgroundImage:
                      "linear-gradient(to right, #00f0ff 1px, transparent 1px), linear-gradient(to bottom, #00f0ff 1px, transparent 1px)",
                    backgroundSize: "16px 16px",
                  }}
                />

                {/* Corner Accents */}
                <div className="absolute top-0 left-0 w-2.5 h-2.5 border-t-2 border-l-2 border-cyan-400/60" />
                <div className="absolute top-0 right-0 w-2.5 h-2.5 border-t-2 border-r-2 border-cyan-400/60" />
                <div className="absolute bottom-0 left-0 w-2.5 h-2.5 border-b-2 border-l-2 border-cyan-400/60" />
                <div className="absolute bottom-0 right-0 w-2.5 h-2.5 border-b-2 border-r-2 border-cyan-400/60" />

                {/* Number Display */}
                <div className="relative">
                  <span className="text-4xl sm:text-6xl lg:text-7xl font-extrabold font-mono tracking-tight bg-gradient-to-b from-white via-cyan-100 to-cyan-400 bg-clip-text text-transparent drop-shadow-[0_0_20px_rgba(0,240,255,0.4)]">
                    {displayValue}
                  </span>
                </div>

                {/* Unit Labels */}
                <div className="mt-2 sm:mt-3 flex flex-col items-center justify-center">
                  <span className="text-xs sm:text-sm font-bold tracking-widest text-cyan-300 font-mono uppercase">
                    {unit.labelVi}
                  </span>
                </div>

                {/* Glow bar at bottom */}
                <div className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent group-hover:via-cyan-400 transition-all duration-300" />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
