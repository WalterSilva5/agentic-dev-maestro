import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as nodemailer from 'nodemailer';

@Injectable()
export class EmailService {
  private readonly logger = new Logger(EmailService.name);
  private transporter: nodemailer.Transporter;

  constructor(private readonly configService: ConfigService) {
    this.initializeTransporter();
  }

  private get appName(): string {
    return this.configService.get<string>('APP_NAME') || 'App';
  }

  private initializeTransporter(): void {
    const host = this.configService.get<string>('EMAIL_HOST') || 'smtp-mail.outlook.com';
    const port = parseInt(this.configService.get<string>('EMAIL_PORT') || '587', 10);
    const user = this.configService.get<string>('EMAIL_USER');
    const pass = this.configService.get<string>('EMAIL_PASSWORD');

    if (!user || !pass) {
      this.logger.warn('Email service not configured. Set EMAIL_USER and EMAIL_PASSWORD environment variables.');
      return;
    }

    this.transporter = nodemailer.createTransport({
      host,
      port,
      secure: port === 465,
      auth: {
        user,
        pass,
      },
    });

    this.logger.log(`Email service initialized with host: ${host}`);
  }

  isConfigured(): boolean {
    return !!this.transporter;
  }

  async sendEmail(to: string, subject: string, html: string): Promise<boolean> {
    if (!this.transporter) {
      this.logger.error('Email service not configured');
      return false;
    }

    const from = this.configService.get<string>('EMAIL_FROM') ||
      this.configService.get<string>('EMAIL_USER');

    try {
      await this.transporter.sendMail({
        from: `"${this.appName}" <${from}>`,
        to,
        subject,
        html,
      });
      this.logger.log(`Email sent to ${to}`);
      return true;
    } catch (error) {
      this.logger.error(`Failed to send email to ${to}: ${error.message}`);
      return false;
    }
  }

  async sendPasswordResetEmail(email: string, userName: string, resetLink: string): Promise<boolean> {
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #e5e7eb; margin: 0; padding: 20px; }
          .container { max-width: 600px; margin: 0 auto; background: linear-gradient(145deg, #1e1e28, #14141e); border-radius: 12px; padding: 40px; }
          h1 { color: #3b82f6; margin-bottom: 20px; }
          p { line-height: 1.6; margin-bottom: 16px; }
          .button { display: inline-block; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 20px 0; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #374151; font-size: 14px; color: #9ca3af; }
          .code { background: #374151; padding: 10px 20px; border-radius: 6px; font-family: monospace; font-size: 18px; letter-spacing: 2px; margin: 20px 0; display: inline-block; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Recuperacao de Senha</h1>
          <p>Ola, ${userName}!</p>
          <p>Voce solicitou a recuperacao de senha da sua conta no ${this.appName}.</p>
          <p>Clique no botao abaixo para redefinir sua senha:</p>
          <a href="${resetLink}" class="button">Redefinir Senha</a>
          <p>Ou copie e cole o link abaixo no seu navegador:</p>
          <p style="word-break: break-all; color: #9ca3af; font-size: 14px;">${resetLink}</p>
          <p><strong>Este link expira em 1 hora.</strong></p>
          <div class="footer">
            <p>Se voce nao solicitou esta recuperacao de senha, ignore este email.</p>
            <p>${this.appName}</p>
          </div>
        </div>
      </body>
      </html>
    `;

    return this.sendEmail(email, `Recuperacao de Senha - ${this.appName}`, html);
  }

  async sendPasswordChangedEmail(email: string, userName: string): Promise<boolean> {
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #e5e7eb; margin: 0; padding: 20px; }
          .container { max-width: 600px; margin: 0 auto; background: linear-gradient(145deg, #1e1e28, #14141e); border-radius: 12px; padding: 40px; }
          h1 { color: #10b981; margin-bottom: 20px; }
          p { line-height: 1.6; margin-bottom: 16px; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #374151; font-size: 14px; color: #9ca3af; }
          .warning { background: #7f1d1d40; border: 1px solid #ef4444; border-radius: 8px; padding: 16px; margin: 20px 0; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Senha Alterada com Sucesso</h1>
          <p>Ola, ${userName}!</p>
          <p>Sua senha foi alterada com sucesso.</p>
          <div class="warning">
            <p><strong>Se voce nao fez esta alteracao</strong>, entre em contato conosco imediatamente.</p>
          </div>
          <div class="footer">
            <p>${this.appName}</p>
          </div>
        </div>
      </body>
      </html>
    `;

    return this.sendEmail(email, `Senha Alterada - ${this.appName}`, html);
  }
}
