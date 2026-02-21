import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', 'sans-serif'],
        mono: ['monospace'],
      },
      colors: {
        'risk-low': '#22c55e',
        'risk-mid': '#eab308',
        'risk-high': '#f97316',
        'risk-severe': '#ef4444',
      },
    },
  },
  plugins: [],
};

export default config;
