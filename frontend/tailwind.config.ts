import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: { colors: { ink: "#17212b", muted: "#65717d", line: "#e7ebef", canvas: "#f7f8fa", accent: "#3759d7" } } },
  plugins: []
};
export default config;
