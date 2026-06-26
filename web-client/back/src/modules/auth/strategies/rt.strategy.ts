import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { AuthService } from 'src/modules/auth/service/auth.service';
import type { User } from 'src/modules/user/entities/user.entity';

@Injectable()
export class RtStrategy extends PassportStrategy(Strategy, 'jwt-refresh') {
  constructor(private authService: AuthService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: process.env.RT_SECRET,
      ignoreExpiration: false
    });
  }

  // Passport JWT já valida a assinatura e expiração do refresh token
  // Verificamos sessionToken apenas se PERMIT_DOUBLE_SESSION estiver desabilitado
  async validate(payload: User): Promise<User> {
    await this.authService.validateRefreshSession(payload);
    return payload;
  }
}
