import { Controller, Get, HttpStatus, Post, Res, UseGuards, Body, Param } from '@nestjs/common';
import { Request } from '@nestjs/common';
import {
  ApiNoContentResponse,
  ApiBearerAuth,
  ApiOkResponse,
  ApiBody,
  ApiTags
} from '@nestjs/swagger';
import { ApiResponse } from '@nestjs/swagger';
import { Response } from 'express';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import { GoogleOAuthGuard } from 'src/modules/auth/guards/google-oauth.guard';
import { OauthService } from 'src/modules/auth/service/oauth.service';
import { User } from 'src/modules/user/entities/user.entity';

import { LoginDto } from '../dto/login.dto';
import { ForgotPasswordDto, ResetPasswordDto, ChangePasswordDto } from '../dto/password-reset.dto';
import { JWTTokenDto } from '../dto/token.dto';
import { AtGuard } from '../guards/at.guard';
import { LocalAuthGuard } from '../guards/local-auth.guard';
import { RtGuard } from '../guards/rt.guard';
import { AuthService } from '../service/auth.service';

@Controller('auth')
@ApiTags('auth')
export class AuthController {
  constructor(
    private readonly authService: AuthService,
    private readonly oauthService: OauthService
  ) {}

  @Post('refresh')
  @UseGuards(RtGuard)
  @ApiOkResponse({ type: JWTTokenDto })
  @ApiBearerAuth()
  async refresh(@AuthenticatedUser() user: User) {
    return this.authService.refreshTokens(user);
  }

  @unprotected()
  @Post('login')
  @UseGuards(LocalAuthGuard)
  @ApiOkResponse({ type: JWTTokenDto })
  @ApiBody({ type: LoginDto })
  async login(
    @AuthenticatedUser() user: User,
    @Res({ passthrough: true }) response: Response
  ) {
    response.status(HttpStatus.OK);
    return this.authService.login(user);
  }

  @Post('logout')
  @UseGuards(AtGuard)
  @ApiNoContentResponse()
  @ApiBearerAuth()
  async logout(
    @AuthenticatedUser() user: User,
    @Res({ passthrough: true }) response: Response
  ) {
    response.status(HttpStatus.OK);
    await this.authService.logout(user);
  }

  @Get('/accounts/google/login')
  @UseGuards(GoogleOAuthGuard)
  @unprotected()
  async googleAuth(@Request() req, @Res() res: Response) {
    console.log('\n\n\nGoogle authentication initiated');
    return this.oauthService.processOuthRedirect(req, res);
  }

  @Get('/accounts/google/redirect')
  @ApiResponse({ status: HttpStatus.NOT_MODIFIED })
  @UseGuards(GoogleOAuthGuard)
  @unprotected()
  async googleAuthRedirect(@Request() req, @Res() res: Response) {
    console.log('\n\n\nGoogle authentication redirect');
    return this.oauthService.processOuthRedirect(req, res);
  }

  @Post('forgot-password')
  @unprotected()
  @ApiOkResponse({ description: 'Email de recuperação enviado (se o email existir)' })
  @ApiBody({ type: ForgotPasswordDto })
  async forgotPassword(@Body() dto: ForgotPasswordDto) {
    return this.authService.forgotPassword(dto.email);
  }

  @Post('reset-password')
  @unprotected()
  @ApiOkResponse({ description: 'Senha alterada com sucesso' })
  @ApiBody({ type: ResetPasswordDto })
  async resetPassword(@Body() dto: ResetPasswordDto) {
    return this.authService.resetPassword(dto.token, dto.newPassword);
  }

  @Get('validate-reset-token/:token')
  @unprotected()
  @ApiOkResponse({ description: 'Token válido' })
  async validateResetToken(@Param('token') token: string) {
    return this.authService.validateResetToken(token);
  }

  @Post('change-password')
  @UseGuards(AtGuard)
  @ApiBearerAuth()
  @ApiOkResponse({ description: 'Senha alterada com sucesso' })
  @ApiBody({ type: ChangePasswordDto })
  async changePassword(
    @AuthenticatedUser() user: User,
    @Body() dto: ChangePasswordDto
  ) {
    return this.authService.changePassword(user.id, dto.currentPassword, dto.newPassword);
  }
}
