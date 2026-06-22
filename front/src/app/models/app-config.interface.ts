export interface AppConfig {
  apiUrl: string;
  production: boolean;
  app?: AppMobileConfig;
}

export interface AppMobileConfig {
  name: string;
  version: string;
  versionCode: number;
  deepLinkHost: string;
  theme: {
    primaryColor: string;
    darkBackground: string;
    statusBarColor: string;
  };
}
