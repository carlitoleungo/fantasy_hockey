// Tailwind build for the app. Colours point at the CSS custom properties in
// app.css, so light/dark switching happens in one place (docs/design-system.md).
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["../templates/**/*.html", "../routes/**/*.py", "../templates.py"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        app: "var(--app)",
        panel: "var(--panel)",
        panel2: "var(--panel-2)",
        line: "var(--line)",
        line2: "var(--line-2)",
        fg: "var(--fg)",
        strong: "var(--strong)",
        muted: "var(--muted)",
        dim: "var(--dim)",
        accent: "var(--accent)",
        accentsoft: "var(--accent-soft)",
        up: "var(--up)",
        down: "var(--down)",
        dtd: "var(--dtd)",
        inj: "var(--inj)",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        cond: ['"Barlow Condensed"', '"Arial Narrow"', "sans-serif-condensed", "sans-serif"],
      },
    },
  },
  plugins: [],
};
