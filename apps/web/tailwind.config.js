/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0F172A', // Slate-900
        card: '#1E293B',       // Slate-800
        border: '#334155',     // Slate-700
        primary: '#8B5CF6',    // Violet-500
        income: '#10B981',     // Emerald-500
        expense: '#F43F5E',    // Rose-500
        mutedText: '#94A3B8',  // Slate-400
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'sans-serif'],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
