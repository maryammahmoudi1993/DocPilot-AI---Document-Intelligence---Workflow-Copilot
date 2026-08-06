/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#7257F5',
          hover: '#6047E8',
          soft: '#EEEAFE',
        },
        lavender: '#F5F2FF',
        page: '#EEECF6',
        app: '#FBFAFD',
        card: '#FFFFFF',
        sidebar: '#F6F3FF',
        text: {
          primary: '#232235',
          secondary: '#77758A',
          muted: '#A3A1AF',
        },
        border: '#E8E6EE',
        divider: '#EFEDF3',
        status: {
          processing: '#65A7F7',
          'processing-bg': '#EAF4FF',
          approved: '#65C99B',
          'approved-bg': '#E9F9F1',
          review: '#F2C95F',
          'review-bg': '#FFF7D9',
          failed: '#F17691',
          'failed-bg': '#FDECEF',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
