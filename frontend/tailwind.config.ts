import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#131722",
        border: "#232838",
        bull: "#26a69a",
        bear: "#ef5350",
      },
    },
  },
  plugins: [],
};

export default config;
