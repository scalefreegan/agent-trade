import type { Config } from 'tailwindcss'
import typography from '@tailwindcss/typography'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          '50': '#FFFF3F',
          '100': '#EEEF20',
          '200': '#DDDF00',
          '300': '#D4D700',
          '400': '#BFD200',
          '500': '#AACC00',
          '600': '#80B918',
          '700': '#55A630',
          '800': '#2B9348',
          '900': '#007F5F',
        },
      },
    },
  },
  plugins: [typography],
} satisfies Config
