/** @type {import('tailwindcss').Config} */
module.exports = {
  // TODO: Content paths para purging em production
  content: [
    "./src/**/*.{html,ts,scss,css}",
  ],

  // TODO: Importante - preservar dark mode do Material
  darkMode: 'class',

  theme: {
    // TODO: Breakpoints customizados (alinhados com a aplicação)
    screens: {
      'xs': '480px',    // Extra small (custom para mobile pequeno)
      'sm': '640px',    // Small (Tailwind default)
      'md': '768px',    // Medium (alinhado com Bootstrap e media queries atuais)
      'lg': '1024px',   // Large
      'xl': '1280px',   // Extra large
      '2xl': '1536px',  // 2X large
    },

    extend: {
      // TODO: Migrar cores do colors.scss
      colors: {
        primary: '#1DB954',
        secondary: '#6A0DAD',
        dark: {
          bg: '#121212',
          text: '#FFFFFF',
          surface: '#1E1E1E',
          border: '#2A2A2A',
          hover: '#333333',
        },
        grayscale: {
          1: '#121212',
          2: '#1E1E1E',
          3: '#2A2A2A',
          4: '#A0A0A0',
          5: '#D0D0D0',
        },
        white: {
          1: '#FFFFFF',
        },
        green: {
          1: '#1DB954',
          2: '#17a347',
        },
        purple: {
          1: '#6A0DAD',
        },
      },

      // TODO: Fonte Inter (já instalada)
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },

      // TODO: Spacing para safe-area (iOS notch, etc)
      spacing: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },

      // TODO: Altura viewport mobile (svh, dvh)
      height: {
        'screen-svh': '100svh',  // Small Viewport Height (mobile com barras)
        'screen-dvh': '100dvh',  // Dynamic Viewport Height
      },

      minHeight: {
        'touch': '48px',  // TODO: Touch target mínimo (WCAG)
        'screen-svh': '100svh',
      },

      maxHeight: {
        'screen-svh': '100svh',
      },

      // TODO: Shadows personalizadas (compatíveis com design atual)
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.15)',
        'modal': '0 10px 40px rgba(29, 185, 84, 0.3)',
      },

      // TODO: Border radius (compatível com design atual)
      borderRadius: {
        'card': '8px',
        'button': '8px',
        'modal': '16px',
      },

      // TODO: Transições suaves
      transitionDuration: {
        '400': '400ms',
      },
    },
  },

  plugins: [
    // TODO: Plugin para estilização de formulários
    require('@tailwindcss/forms'),

    // TODO: Plugin para tipografia rich text
    require('@tailwindcss/typography'),
    // DaisyUI - componentes prontos (padrões e tema)
    require('daisyui'),
  ],

  // DaisyUI configuration (optional)
  daisyui: {
    themes: [
      {
        brand: {
          primary: '#1DB954',
          secondary: '#6A0DAD',
          accent: '#17a347',
          neutral: '#1E1E1E',
          'base-100': '#121212',
          info: '#3ABFF8',
          success: '#1DB954',
          warning: '#FBBD23',
          error: '#F87272'
        }
      },
      'dark'
    ],
    darkTheme: 'dark'
  }
}
