/** DAPRO design tokens. Colors come from CSS variables in src/styles/index.css (see docs/design/DESIGN_SYSTEM.md). */
import animate from "tailwindcss-animate";

const v = (name) => `hsl(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.5rem" },
    extend: {
      fontFamily: { sans: ["Inter Variable", "Inter", "system-ui", "Segoe UI", "sans-serif"] },
      fontSize: { "2xs": ["0.6875rem", { lineHeight: "1rem" }] },
      colors: {
        border: v("border"), input: v("input"), ring: v("ring"), background: v("background"),
        foreground: v("foreground"), surface: v("surface"),
        primary: { DEFAULT: v("primary"), foreground: v("primary-foreground"), soft: v("primary-soft") },
        navy: { DEFAULT: v("navy"), 800: v("navy-800"), 700: v("navy-700"), foreground: v("navy-foreground") },
        teal: { DEFAULT: v("teal"), soft: v("teal-soft") },
        success: { DEFAULT: v("success"), soft: v("success-soft") },
        warning: { DEFAULT: v("warning"), soft: v("warning-soft") },
        danger: { DEFAULT: v("danger"), soft: v("danger-soft") },
        muted: { DEFAULT: v("muted"), foreground: v("muted-foreground") },
        accent: { DEFAULT: v("accent"), foreground: v("accent-foreground") },
        card: { DEFAULT: v("card"), foreground: v("card-foreground") },
        popover: { DEFAULT: v("popover"), foreground: v("popover-foreground") },
      },
      borderRadius: { lg: "10px", md: "8px", sm: "6px" },
      boxShadow: {
        card: "0 1px 2px 0 rgb(16 42 86 / 0.04), 0 1px 3px 0 rgb(16 42 86 / 0.06)",
        pop: "0 10px 30px -10px rgb(16 42 86 / 0.25)",
      },
      keyframes: { shimmer: { "100%": { transform: "translateX(100%)" } } },
    },
  },
  plugins: [animate],
};
