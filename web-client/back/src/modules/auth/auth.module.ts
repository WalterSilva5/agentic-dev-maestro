import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { CreditAccountModule } from 'src/modules/credit-account/credit-account.module';
import { EmailModule } from 'src/modules/email/email.module';
import { UserModule } from 'src/modules/user/user.module';

import { AuthController } from './controller/auth.controller';
import { AuthService } from './service/auth.service';
import { OauthService } from './service/oauth.service';
import { AtStrategy } from './strategies/at.strategy';
import { GoogleStrategy } from './strategies/google-auth.strategy';
import { LocalStrategy } from './strategies/local.strategy';
import { RtStrategy } from './strategies/rt.strategy';

// GoogleStrategy throws on boot if GOOGLE_CLIENT_ID is blank, so only register it
// when Google OAuth is actually configured. Leave the credentials empty to disable social login.
const googleProviders = process.env.GOOGLE_CLIENT_ID ? [GoogleStrategy] : [];

@Module({
  imports: [UserModule, PrismaModule, JwtModule.register({}), CreditAccountModule, EmailModule],
  controllers: [AuthController],
  providers: [
    AuthService,
    LocalStrategy,
    AtStrategy,
    RtStrategy,
    OauthService,
    ...googleProviders
  ]
})
export class AuthModule {}
