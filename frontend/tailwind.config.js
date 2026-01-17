/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        monad: {
          purple: '#836EF9',
          'purple-dark': '#5f4bb6',
          'purple-glow': 'rgba(131, 110, 249, 0.5)',
          black: '#000000',
          surface: '#0E0E0E',
          'surface-light': '#1A1A1A',
          border: '#27272A',
        },
        risk: {
          safe: '#34D399',      // emerald-400
          medium: '#22D3EE',    // cyan-400
          high: '#A78BFA',      // purple-400
          danger: '#FB7185',    // rose-400
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'grid-pattern': "linear-gradient(to right, #111 1px, transparent 1px), linear-gradient(to bottom, #111 1px, transparent 1px)",
      },
      backgroundSize: {
        'grid-size': '40px 40px',
      }
    },
  },
  plugins: [],
}