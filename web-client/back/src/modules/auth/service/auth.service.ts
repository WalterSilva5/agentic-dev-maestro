/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable complexity */
import { UnauthorizedException, BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
// ...existing imports...
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import * as crypto from 'crypto';
import { PrismaService } from 'src/database/prisma/prisma.service';
import { CreditAccountService } from 'src/modules/credit-account/credit-account.service';
import { EmailQueue } from 'src/modules/email/email.queue';
import type { User } from 'src/modules/user/entities/user.entity';
import { UserService } from 'src/modules/user/user.service';

import type { RegisterDto } from '../dto/register.dto';
import type { JWTTokenDto } from '../dto/token.dto';

@Injectable()
export class AuthService {
  constructor(
    private readonly userService: UserService,
    private readonly jwtService: JwtService,
    private readonly prisma: PrismaService,
    private readonly creditAccountService: CreditAccountService,
    private readonly emailQueue: EmailQueue
  ) {}

  async validateUser(email: string, password: string) {
    let user = undefined;

    try {
      user = await this.userService.findByEmail(email, { password: true });
    } catch (_error: unknown) {}

    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new BadRequestException('Usuário ou senha inválidos');
    }

    return user;
  }

  // Validação de sessão apenas para refresh tokens (permite revogação)
  async validateRefreshSession(user: User): Promise<void> {
    // Só verifica sessionToken se PERMIT_DOUBLE_SESSION estiver desabilitado
    if (process.env.PERMIT_DOUBLE_SESSION === 'false') {
      const userInDb = await this.userService.findById(user.id, { sessionToken: true });

      if (!userInDb || !userInDb.sessionToken) {
        throw new UnauthorizedException('Sessão inválida');
      }

      if (user.sessionToken !== userInDb.sessionToken) {
        throw new UnauthorizedException('Já existe uma sessão ativa para esta conta');
      }
    }
  }

  async login(user: User): Promise<JWTTokenDto> {
    // Ensure daily credits are granted upon login
    await this.creditAccountService.ensureDailyCredits(user.id);
    const userInDb = await this.userService.findById(user.id);
    return this.getTokens(userInDb);
  }

  async logout(user: User): Promise<void> {
    await this.prisma.user.update({
      where: {
        id: user.id
      },
      data: {
        sessionToken: null
      }
    });
  }

  async createUser(dto: RegisterDto): Promise<JWTTokenDto> {
    const newUser = await this.userService.create(dto);
    return this.getTokens(newUser);
  }

  async refreshTokens(user: User) {
    const userInDb = await this.userService.findById(user.id, { sessionToken: true });

    if (!userInDb || !userInDb.sessionToken) {
      throw new UnauthorizedException('Sessão expirada');
    }

    return this.getTokens(userInDb);
  }

  async updateSessionToken(user: User, sessionToken: string) {
    await this.prisma.user.update({
      where: {
        id: user.id
      },
      data: {
        sessionToken
      }
    });
  }

  hashData(data: string) {
    return bcrypt.hash(data, 10);
  }

  async getTokens(user: User): Promise<JWTTokenDto> {
    const sessionToken = crypto.randomBytes(16).toString('hex');

    // Payload otimizado - apenas dados essenciais
    const payload = {
      sub: user.id,
      id: user.id,
      email: user.email,
      role: user.role,
      sessionToken
    };

    const [accessToken, refreshToken] = await Promise.all([
      this.jwtService.signAsync(payload, {
        secret: process.env.AT_SECRET,
        expiresIn: process.env.JWT_ACCESS_LIFETIME
      }),
      this.jwtService.signAsync(payload, {
        secret: process.env.RT_SECRET,
        expiresIn: process.env.JWT_REFRESH_LIFETIME
      })
    ]);

    await this.updateSessionToken(user, sessionToken);

    return {
      refreshToken,
      accessToken,
      user
    };
  }

  async forgotPassword(email: string): Promise<{ message: string }> {
    // Check if user exists
    const user = await this.prisma.user.findUnique({
      where: { email }
    });

    // Always return success to prevent email enumeration
    if (!user) {
      return { message: 'Se o email existir em nossa base, você receberá instruções de recuperação.' };
    }

    // Invalidate any existing tokens for this email
    await this.prisma.passwordResetToken.updateMany({
      where: {
        email,
        usedAt: null,
        expiresAt: { gt: new Date() }
      },
      data: { usedAt: new Date() }
    });

    // Generate a secure token
    const token = crypto.randomBytes(32).toString('hex');
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000); // 1 hour from now

    // Save token to database
    await this.prisma.passwordResetToken.create({
      data: {
        email,
        token,
        expiresAt
      }
    });

    // Send email with reset link
    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:4200';
    const resetLink = `${frontendUrl}/reset-password?token=${token}`;

    await this.emailQueue.enqueuePasswordReset(email, user.firstName, resetLink);

    return { message: 'Se o email existir em nossa base, você receberá instruções de recuperação.' };
  }

  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    // Find valid token
    const resetToken = await this.prisma.passwordResetToken.findUnique({
      where: { token }
    });

    if (!resetToken) {
      throw new BadRequestException('Token inválido ou expirado.');
    }

    if (resetToken.usedAt) {
      throw new BadRequestException('Este token já foi utilizado.');
    }

    if (resetToken.expiresAt < new Date()) {
      throw new BadRequestException('Token expirado. Solicite uma nova recuperação de senha.');
    }

    // Find user by email
    const user = await this.prisma.user.findUnique({
      where: { email: resetToken.email }
    });

    if (!user) {
      throw new NotFoundException('Usuário não encontrado.');
    }

    // Hash new password
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update user password and invalidate all sessions
    await this.prisma.user.update({
      where: { id: user.id },
      data: {
        password: hashedPassword,
        sessionToken: null
      }
    });

    // Mark token as used
    await this.prisma.passwordResetToken.update({
      where: { id: resetToken.id },
      data: { usedAt: new Date() }
    });

    // Send confirmation email
    await this.emailQueue.enqueuePasswordChanged(user.email, user.firstName);

    return { message: 'Senha alterada com sucesso!' };
  }

  async changePassword(userId: number, currentPassword: string, newPassword: string): Promise<{ message: string }> {
    // Get user with password
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: { id: true, email: true, firstName: true, password: true }
    });

    if (!user) {
      throw new NotFoundException('Usuário não encontrado.');
    }

    // Verify current password
    const isPasswordValid = await bcrypt.compare(currentPassword, user.password);
    if (!isPasswordValid) {
      throw new BadRequestException('Senha atual incorreta.');
    }

    // Hash new password
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update password
    await this.prisma.user.update({
      where: { id: userId },
      data: { password: hashedPassword }
    });

    // Send confirmation email
    await this.emailQueue.enqueuePasswordChanged(user.email, user.firstName);

    return { message: 'Senha alterada com sucesso!' };
  }

  async validateResetToken(token: string): Promise<{ valid: boolean; email?: string }> {
    const resetToken = await this.prisma.passwordResetToken.findUnique({
      where: { token }
    });

    if (!resetToken || resetToken.usedAt || resetToken.expiresAt < new Date()) {
      return { valid: false };
    }

    return { valid: true, email: resetToken.email };
  }
}
