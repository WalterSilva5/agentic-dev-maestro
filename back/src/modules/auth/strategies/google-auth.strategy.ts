import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import type { VerifyCallback } from 'passport-google-oauth20';
import { Strategy } from 'passport-google-oauth20';
import config from 'src/utils/config';

@Injectable()
export class GoogleStrategy extends PassportStrategy(Strategy, 'google') {
  constructor() {
    super({
      clientID: config.google.clientID,
      clientSecret: config.google.clientSecret,
      callbackURL: config.google.callbackURL,
      scope: ['email', 'profile']
    });
  }
  async validate(
    accessToken: string,
    refreshToken: string,
    profile: any,
    done: VerifyCallback
  ): Promise<any> {
    const { name, emails } = profile;
    const user = {
      email: emails[0].value,
      firstName: name.givenName,
      lastName: name.familyName,
      accessToken,
      refreshToken
    };
    done(null, user);
  }
}
