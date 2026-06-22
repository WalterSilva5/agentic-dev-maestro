import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import type { User } from 'src/modules/user/entities/user.entity';

@Injectable()
export class AtStrategy extends PassportStrategy(Strategy, 'jwt') {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: process.env.AT_SECRET,
      ignoreExpiration: false
    });
  }

  // Passport JWT já valida a assinatura e expiração do token
  // Não precisamos de verificação adicional no banco para cada requisição
  validate(payload: User): User {
    return payload;
  }
}
