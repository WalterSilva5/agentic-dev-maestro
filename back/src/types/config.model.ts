export type ConfigModel = {
  google: {
    clientID: string;
    clientSecret: string;
    callbackURL: string;
  };
  session: {
    secret: string;
  };
  frontendUrl: string;
};
