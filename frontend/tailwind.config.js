/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'rgb(var(--photonv-primary) / <alpha-value>)',
          soft: 'rgb(var(--photonv-primary-soft) / <alpha-value>)',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
};
