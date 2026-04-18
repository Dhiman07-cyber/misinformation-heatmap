/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./frontend/index.html",
    "./frontend/dashboard.html",
    "./frontend/map/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        saffron: {
          DEFAULT: '#E87722',
          light: '#FF9933',
          dark: '#c4601a',
        },
        green: {
          DEFAULT: '#138808',
          light: '#1ea50e',
        },
        navy: '#000080',
        bg: '#FAFAF7',
        'bg-card': '#FFFFFF',
        'bg-card-hover': '#F5F5F0',
        border: '#E8E8E0',
        'text-primary': '#1A1A1A',
        'text-secondary': '#555555',
        'text-muted': '#888888',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        outfit: ['Outfit', 'sans-serif'],
      },
      boxShadow: {
        'sm': '0 2px 8px rgba(0,0,0,0.08)',
        'md': '0 4px 20px rgba(0,0,0,0.10)',
        'lg': '0 8px 40px rgba(0,0,0,0.12)',
      },
      borderRadius: {
        'DEFAULT': '16px',
        'sm': '10px',
      },
      animation: {
        'pulse': 'pulse 2s infinite',
        'pulse-red': 'pulse-red 1.5s infinite',
      },
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 0 0 rgba(19,136,8,0.4)' },
          '50%': { opacity: '0.8', boxShadow: '0 0 0 5px rgba(19,136,8,0)' },
        },
      },
    },
  },
  plugins: [],
}
