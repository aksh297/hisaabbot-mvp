/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        paper: "#FDFBF7",
        parchment: "#F4F1DE",
        chatbg: "#EFEAE2",
        ink: "#1E3F33",
        inkhover: "#2A5244",
        ochre: "#D49A00",
        ochrelight: "#F2CC8F",
        wagreen: "#128C7E",
        wadark: "#075E54",
        wamsg: "#DCF8C6",
        terracotta: "#C05640",
      },
      fontFamily: {
        heading: ['"Cabinet Grotesk"', '"Outfit"', "sans-serif"],
        body: ['"IBM Plex Sans"', '"Noto Sans Devanagari"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
      backgroundImage: {
        "chat-pattern": "url('https://www.transparenttextures.com/patterns/cubes.png')",
      },
      animation: {
        "fade-up": "fadeUp 0.5s ease-out both",
        "fade-in": "fadeIn 0.4s ease-out both",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
