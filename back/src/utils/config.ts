import type { ConfigModel } from 'src/types/config.model';

export const config: ConfigModel = {
  google: {
    clientID: process.env.GOOGLE_CLIENT_ID,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    callbackURL: process.env.GOOGLE_CALLBACK_URL
  },
  session: {
    secret: process.env.AT_SECRET
  },
  frontendUrl: process.env.FRONTEND_URL
};

export default config;
