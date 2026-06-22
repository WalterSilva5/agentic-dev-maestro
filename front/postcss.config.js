module.exports = {
  // Tailwind v3 via PostCSS plugin (compatible with Angular 20)
  // NOTE: Using v3 plugin entry to avoid the v4-specific error.
  plugins: [
    require('tailwindcss'),
    require('autoprefixer'),
  ],
};
