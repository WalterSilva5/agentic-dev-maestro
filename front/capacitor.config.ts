import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.example.app',
  appName: 'Fullstack Template',
  webDir: 'dist/fullstack-template-front/browser',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#181818',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#181818',
    },
    Keyboard: {
      resizeOnFullScreen: true,
    },
  },
};

export default config;
