import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./store/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0F766E",
          hover: "#115E59",
          light: "#CCFBF1",
        },
        secondary: {
          DEFAULT: "#1E3A8A",
          light: "#DBEAFE",
        },
        accent: {
          DEFAULT: "#F59E0B",
          hover: "#D97706",
          light: "#FEF3C7",
        },
        error: {
          DEFAULT: "#DC2626",
          light: "#FEE2E2",
        },
        success: {
          DEFAULT: "#16A34A",
          light: "#DCFCE7",
        },
        background: "#F8FAFC",
        surface: "#FFFFFF",
        muted: "#F3F4F6",
        border: "#E5E7EB",
        "text-primary": "#111827",
        "text-secondary": "#6B7280",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"],
      },
      boxShadow: {
        card: "0 10px 30px rgba(0, 0, 0, 0.12)",
        toast: "0 4px 12px rgba(0, 0, 0, 0.1)",
      },
    },
  },
  plugins: [],
};

export default config;
