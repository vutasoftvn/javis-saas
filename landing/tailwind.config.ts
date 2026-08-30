import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: "#070C18",
          dark: "#04070E",
          card: "#0D172A",
          elevated: "#141C2E",
        },
        cosa: {
          cyan: "#00F0FF",
          sky: "#38BDF8",
          blue: "#0072FF",
          emerald: "#10B981",
          rose: "#F43F5E",
          amber: "#F59E0B",
          violet: "#8B5CF6",
          darker: "#04070E",
          surface: "#0D172A",
          surfaceLight: "#141C2E",
          border: "#1E293B",
          borderGlow: "rgba(0, 240, 255, 0.3)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "cyan-glow": "radial-gradient(circle, rgba(0,240,255,0.15) 0%, rgba(0,0,0,0) 70%)",
        "blue-glow": "radial-gradient(circle, rgba(0,114,255,0.15) 0%, rgba(0,0,0,0) 70%)",
      },
      animation: {
        "pulse-glow": "pulseGlow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scanline": "scanline 8s linear infinite",
        "float": "float 4s ease-in-out infinite",
        "shimmer": "shimmer 2.5s infinite",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "0.4", transform: "scale(1)" },
          "50%": { opacity: "0.8", transform: "scale(1.05)" },
        },
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(1000%)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
