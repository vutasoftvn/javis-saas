"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, ArrowRight, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface EmailSubscribeFormProps {
  className?: string;
  placeholder?: string;
}

export function EmailSubscribeForm({
  className = "w-full max-w-3xl mx-auto my-6 px-4",
  placeholder = "Nhập email...",
}: EmailSubscribeFormProps) {
  const [email, setEmail] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<{
    message: string;
    simulated?: boolean;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      setError("Vui lòng nhập địa chỉ email hợp lệ.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/early-access", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: cleanEmail,
          fullName: "Thành viên COSA Sớm",
          phone: "Đăng ký qua Email",
          company: "Khách hàng Tiềm năng",
          priorityInterest: "Đăng ký nhận thông báo phát hành sớm COSA OS 2027",
          website: honeypot, // Honeypot trap
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Đăng ký chưa thành công, vui lòng thử lại sau.");
      }

      setSuccessData({
        message: data.message || "Đăng ký thành công!",
        simulated: data.simulated,
      });
      setEmail("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Đã có lỗi xảy ra. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={className}>
      <AnimatePresence mode="wait">
        {!successData ? (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="relative"
          >
            <form onSubmit={handleSubmit} className="relative flex flex-col sm:flex-row gap-3">
              {/* Honeypot field (hidden for users, bots fill this) */}
              <input
                type="text"
                name="website"
                value={honeypot}
                onChange={(e) => setHoneypot(e.target.value)}
                tabIndex={-1}
                autoComplete="off"
                className="sr-only"
                aria-hidden="true"
              />

              {/* Input container */}
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-5 h-5 text-cyan-400" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder={placeholder}
                  required
                  disabled={loading}
                  className="w-full pl-12 pr-4 py-3.5 rounded-xl bg-slate-900/90 border border-cyan-500/30 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 text-sm sm:text-base font-sans backdrop-blur-xl transition-all shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)]"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 text-slate-950 font-bold font-sans text-sm sm:text-base flex items-center justify-center gap-2 hover:opacity-95 hover:shadow-[0_0_25px_rgba(0,240,255,0.5)] active:scale-[0.98] transition-all duration-200 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed shrink-0"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Đang xử lý...</span>
                  </>
                ) : (
                  <>
                    <span>Đăng kí</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Error message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-3 p-3 rounded-lg bg-red-950/60 border border-red-500/40 text-red-300 text-xs sm:text-sm flex items-center gap-2 font-mono"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
                <span>{error}</span>
              </motion.div>
            )}
          </motion.div>
        ) : (
          /* Success Card (Không gửi mã trước, thông báo sẽ gửi thư mời kèm mã sau) */
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="p-5 sm:p-6 rounded-2xl bg-gradient-to-b from-slate-900 via-[#071324] to-[#070c18] border border-cyan-500/50 shadow-[0_0_40px_rgba(0,240,255,0.2)] text-center relative overflow-hidden"
          >
            <div className="w-12 h-12 mx-auto rounded-full bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-300 mb-3 shadow-[0_0_20px_rgba(0,240,255,0.3)]">
              <CheckCircle2 className="w-6 h-6" />
            </div>

            <h4 className="text-lg sm:text-xl font-bold text-white mb-2">
              Đăng Ký Thành Công!
            </h4>
            <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto mb-5 leading-relaxed">
              MIVA Corp đã ghi nhận email của bạn. Chúng tôi sẽ gửi thư mời trải nghiệm chính thức kèm mã kích hoạt qua email của bạn trước ngày ra mắt.
            </p>

            <button
              type="button"
              onClick={() => setSuccessData(null)}
              className="text-xs text-slate-400 hover:text-cyan-300 underline font-mono transition-colors cursor-pointer"
            >
              ← Đăng ký thêm địa chỉ email khác
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
