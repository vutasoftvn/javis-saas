"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Check,
  Target,
  AlertTriangle,
  Bot,
  Zap,
} from "lucide-react";

interface PersonaDiscoveryWizardProps {
  email: string;
  userSegment?: string;
  projectName?: string;
  onComplete?: () => void;
  onSkip?: () => void;
}

const PROJECT_GOALS = [
  {
    id: "study_rnd",
    title: "Đồ án / Nghiên cứu học tập & R&D",
    desc: "Thử nghiệm công nghệ AI mới, làm luận văn, nghiên cứu ứng dụng thực tiễn",
    tag: "Học tập & Nghiên cứu",
  },
  {
    id: "prd_discovery",
    title: "Nghiên cứu thị trường & Lập PRD Sản phẩm",
    desc: "Khảo sát chân dung khách hàng, phân tích đối thủ & xây dựng lộ trình 12 tuần",
    tag: "Khởi tạo Dự án",
  },
  {
    id: "mkt_growth",
    title: "Tự động hóa Content & Tiếp thị B2B",
    desc: "Xây dựng kênh lead đều đặn cùng Chuyên viên CMO Nova và VP Sales Rex",
    tag: "Tăng trưởng & Sales",
  },
  {
    id: "finance_governance",
    title: "Kế toán TT 58/TT-BTC & Quản trị dòng tiền",
    desc: "Kiểm soát chi tiêu, dự báo runway & chốt chặn rủi ro cùng CFO Apex",
    tag: "Tài chính & Pháp lý",
  },
  {
    id: "okr_operations",
    title: "Vận hành chiến lược OKRs & Điều phối Task",
    desc: "Phân rã mục tiêu lớn thành các Initiatives và Tasks Kanban hàng tuần cùng CSO Iris",
    tag: "Vận hành tự trị",
  },
];

const CHALLENGES = [
  {
    id: "solo_overwhelmed",
    label: "Quá tải vì làm một mình",
    desc: "Phải gánh vác mọi khâu từ marketing, kế toán đến sản phẩm, thiếu thời gian sâu",
  },
  {
    id: "lack_methodology",
    label: "Thiếu phương pháp lập kế hoạch",
    desc: "Ý tưởng nhiều nhưng mơ hồ, không rõ lộ trình thực thi theo từng tuần",
  },
  {
    id: "compliance_finance",
    label: "Rủi ro pháp lý & thuế / tài chính",
    desc: "Chưa nắm vững hóa đơn, dòng tiền và quy định kế toán Thông tư 58/TT-BTC",
  },
  {
    id: "fragmented_tools",
    label: "Công cụ rời rạc, kiến thức phân tán",
    desc: "Dữ liệu bị rải rác giữa Notion, Excel, Google Docs và Chatbot không đồng bộ",
  },
];

const AI_LEVELS = [
  {
    level: "L0",
    name: "Cố Vấn Quan Sát (Advisor)",
    desc: "AI chỉ phân tích số liệu, gợi ý ý tưởng và cảnh báo rủi ro khi bạn chủ động đặt câu hỏi.",
    color: "border-cosa-cyan/40 bg-cosa-cyan/5",
  },
  {
    level: "L1",
    name: "Đề Xuất & Chờ Duyệt (Khuyên dùng)",
    desc: "AI tự động soạn thảo chiến lược, PRD, content hoặc hóa đơn; bạn bấm duyệt (Human-in-the-loop) trước khi kích hoạt.",
    color: "border-cosa-emerald/50 bg-cosa-emerald/5",
    recommended: true,
  },
  {
    level: "L2",
    name: "Tự Động Hóa Bán Phần (Autonomous)",
    desc: "Giao phó toàn bộ tác vụ định kỳ (quét tin, theo dõi blocker OKR, tổng hợp báo cáo tuần) tự chạy ngầm.",
    color: "border-cosa-violet/40 bg-cosa-violet/5",
  },
];

export const PersonaDiscoveryWizard: React.FC<PersonaDiscoveryWizardProps> = ({
  email,
  userSegment = "OPC",
  projectName = "Dự án của bạn",
  onComplete,
  onSkip,
}) => {
  const [step, setStep] = useState(1);
  const [selectedGoal, setSelectedGoal] = useState(PROJECT_GOALS[1].title);
  const [selectedChallenges, setSelectedChallenges] = useState<string[]>([CHALLENGES[0].label]);
  const [aiLevel, setAiLevel] = useState<"L0" | "L1" | "L2">("L1");
  const [loading, setLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const toggleChallenge = (label: string) => {
    if (selectedChallenges.includes(label)) {
      setSelectedChallenges(selectedChallenges.filter((c) => c !== label));
    } else {
      if (selectedChallenges.length < 2) {
        setSelectedChallenges([...selectedChallenges, label]);
      } else {
        setSelectedChallenges([selectedChallenges[1], label]);
      }
    }
  };

  const handleFinish = async () => {
    setLoading(true);
    try {
      await fetch("/api/persona-discovery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          firstProjectGoal: selectedGoal,
          biggestChallenge: selectedChallenges,
          aiAutonomyLevel: aiLevel,
          targetTimelineWeeks: 12,
        }),
      });
      setIsSuccess(true);
      if (onComplete) onComplete();
    } catch (err) {
      console.error("[Persona Discovery Save Error]:", err);
      setIsSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="py-8 text-center space-y-5 animate-fadeIn">
        <div className="w-16 h-16 rounded-full bg-cosa-emerald/20 border border-cosa-emerald flex items-center justify-center mx-auto shadow-[0_0_30px_rgba(16,185,129,0.5)]">
          <CheckCircle2 className="w-8 h-8 text-cosa-emerald" />
        </div>
        <div className="space-y-2">
          <h3 className="text-2xl font-bold text-white">Blueprint Đã Được Lưu Trữ!</h3>
          <p className="text-sm text-slate-300 max-w-md mx-auto">
            Không gian làm việc cho <strong>{projectName}</strong> ({userSegment}) đã được cấu hình sẵn sàng với chính sách AI <strong>Cấp độ {aiLevel}</strong>.
          </p>
        </div>
        <div className="p-4 rounded-2xl bg-[#04070e] border border-slate-800 max-w-md mx-auto text-xs text-slate-400 font-mono text-left space-y-1.5">
          <div className="text-cosa-emerald font-bold">• Gói kích hoạt: Free Discovery (01 Workspace · 01 Project)</div>
          <div>• Mục tiêu: <span className="text-white">{selectedGoal}</span></div>
          <div>• Rào cản trọng tâm: <span className="text-slate-300">{selectedChallenges.join(", ")}</span></div>
        </div>
        <div className="pt-2">
          <a
            href="#features"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cosa-cyan to-cosa-blue text-xs font-bold text-slate-950 hover:brightness-110 transition-all"
          >
            <span>Khám phá các Chuyên viên AI của COSA OS</span>
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Progress Bar & Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div className="inline-flex items-center gap-1.5 font-mono text-cosa-cyan">
            <Sparkles className="w-3.5 h-3.5" />
            <span>BƯỚC {step}/3 · THIẾT LẬP BLUEPRINT DỰ ÁN</span>
          </div>
          {onSkip && (
            <button
              type="button"
              onClick={onSkip}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              Để sau
            </button>
          )}
        </div>
        <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cosa-cyan to-cosa-emerald transition-all duration-300"
            style={{ width: `${(step / 3) * 100}%` }}
          />
        </div>
      </div>

      {/* Step 1: Goal of 1st Project */}
      {step === 1 && (
        <div className="space-y-4 animate-fadeIn">
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <Target className="w-5 h-5 text-cosa-cyan" />
              <span>Mục tiêu của Dự án duy nhất đầu tiên của bạn?</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Gói Free cấp quyền cho <strong>01 Workspace &amp; 01 Project</strong>. Bạn muốn AI tập trung hỗ trợ đầu việc nào nhất?
            </p>
          </div>

          <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
            {PROJECT_GOALS.map((g) => {
              const isSelected = selectedGoal === g.title;
              return (
                <div
                  key={g.id}
                  onClick={() => setSelectedGoal(g.title)}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex items-start justify-between gap-3 ${
                    isSelected
                      ? "bg-cosa-cyan/10 border-cosa-cyan shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                      : "bg-[#04070e] border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">{g.title}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                        {g.tag}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{g.desc}</p>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 mt-0.5 ${
                      isSelected
                        ? "border-cosa-cyan bg-cosa-cyan text-slate-950 font-bold"
                        : "border-slate-700"
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cosa-cyan text-slate-950 font-bold text-xs hover:brightness-110 transition-all"
            >
              <span>Tiếp tục</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Biggest Challenges */}
      {step === 2 && (
        <div className="space-y-4 animate-fadeIn">
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-cosa-amber" />
              <span>Thách thức lớn nhất đang cản trở tiến độ?</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Chọn 1 đến 2 yếu tố khiến bạn mất nhiều thời gian nhất mỗi tuần.
            </p>
          </div>

          <div className="space-y-2.5">
            {CHALLENGES.map((ch) => {
              const isSelected = selectedChallenges.includes(ch.label);
              return (
                <div
                  key={ch.id}
                  onClick={() => toggleChallenge(ch.label)}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex items-start justify-between gap-3 ${
                    isSelected
                      ? "bg-cosa-amber/10 border-cosa-amber shadow-[0_0_15px_rgba(245,158,11,0.15)]"
                      : "bg-[#04070e] border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-white">{ch.label}</span>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{ch.desc}</p>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 mt-0.5 ${
                      isSelected
                        ? "border-cosa-amber bg-cosa-amber text-slate-950 font-bold"
                        : "border-slate-700"
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Quay lại</span>
            </button>
            <button
              type="button"
              onClick={() => setStep(3)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cosa-cyan text-slate-950 font-bold text-xs hover:brightness-110 transition-all"
            >
              <span>Tiếp tục</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: AI Autonomy & Governance */}
      {step === 3 && (
        <div className="space-y-4 animate-fadeIn">
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <Bot className="w-5 h-5 text-cosa-emerald" />
              <span>Mức độ tự chủ mong muốn giao cho 6 AI Worker?</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Bạn có thể điều chỉnh chính sách kiểm soát (Agent Policy) bất kỳ lúc nào trong Workspace.
            </p>
          </div>

          <div className="space-y-2.5">
            {AI_LEVELS.map((al) => {
              const isSelected = aiLevel === al.level;
              return (
                <div
                  key={al.level}
                  onClick={() => setAiLevel(al.level as "L0" | "L1" | "L2")}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-start justify-between gap-3 ${
                    isSelected
                      ? al.color + " shadow-[0_0_15px_rgba(16,185,129,0.15)]"
                      : "bg-[#04070e] border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-cosa-cyan px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                        {al.level}
                      </span>
                      <span className="text-xs font-bold text-white">{al.name}</span>
                      {al.recommended && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cosa-emerald/20 border border-cosa-emerald/50 text-cosa-emerald">
                          Khuyên dùng
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{al.desc}</p>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 mt-0.5 ${
                      isSelected
                        ? "border-cosa-emerald bg-cosa-emerald text-slate-950 font-bold"
                        : "border-slate-700"
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Quay lại</span>
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={handleFinish}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cosa-emerald to-teal-400 text-slate-950 font-extrabold text-xs hover:brightness-110 transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] disabled:opacity-50"
            >
              <Zap className="w-4 h-4" />
              <span>{loading ? "Đang lưu Blueprint..." : "Hoàn Tất & Lưu Blueprint"}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
