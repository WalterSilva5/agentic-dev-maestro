import {
  BadRequestException,
  NotFoundException,
  Logger,
  HttpStatus
} from '@nestjs/common';
import { Request, Res } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Response } from 'express';
import { Messages } from 'src/enums/messages.enum';
import { RegisterDto } from 'src/modules/auth/dto/register.dto';
import { UserService } from 'src/modules/user/user.service';
import { config } from 'src/utils/config';

import { AuthService } from './auth.service';

@Injectable()
export class OauthService {
  private readonly logger = new Logger(OauthService.name);
  constructor(
    private readonly userService: UserService,
    private readonly authService: AuthService
  ) {}

  private async registerUserAndReturnToken(
    userData: RegisterDto,
    @Res() res: Response
  ): Promise<void> {
    const newUser = new RegisterDto();

    newUser.firstName = userData.firstName;
    newUser.lastName = userData.lastName;
    newUser.email = userData.email;
    newUser.password = '';

    try {
      await this.userService.create(newUser);
      const user = await this.userService.findByEmail(userData.email);
      await this.generateTokenAndRedirect(user, res);
    } catch (error) {
      this.logger.error(error);
      throw new BadRequestException(Messages.USER_CREATE_ERROR);
    }
  }

  private async generateTokenAndRedirect(user: any, @Res() res: Response): Promise<void> {
    const tokens = await this.authService.getTokens(user);
    const url = this.getRedirectUrl(tokens);
    res.redirect(HttpStatus.FOUND, url);
  }

  private async googleLogin(@Request() req: any) {
    if (!req.user) throw new NotFoundException(Messages.USER_NOT_FOUND);

    return {
      message: Messages.USER_INFORMATION_FROM_GOOGLE,
      user: req.user
    };
  }

  private getRedirectUrl(tokens: any) {
    return (
      config.frontendUrl +
      '/auth/google/callback?access=' +
      tokens.accessToken +
      '&refresh=' +
      tokens.refreshToken
    );
  }

  public async processOuthRedirect(@Request() req: Request, @Res() res: Response) {
    try {
      const { user }: any = await this.googleLogin(req);
      console.log('\n\n\nprocessOuthRedirect ~ googleLogin user google', user);
      const userDb = await this.userService.findByEmail(user.email);
      //if not found, register
      console.log('\n\n\nprocessOuthRedirect ~ userDb', userDb);
      if (!userDb) {
        console.log('\n\n\nprocessOuthRedirect ~ registering user', user);
        await this.registerUserAndReturnToken(user, res);
        // registerUserAndReturnToken performs a redirect, so stop further processing
        return;
      }
      console.log('\n\n\nuserDb', userDb);
      return this.generateTokenAndRedirect(userDb, res);
    } catch (error) {
      this.logger.error('OAuth redirect error:', error);
      // Redirect to login with error parameter
      res.redirect(`${config.frontendUrl}/auth/login?error=oauth_failed`);
    }
  }
}
