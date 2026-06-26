import { Process, Processor } from '@nestjs/bull';
import { Logger } from '@nestjs/common';
import { Job } from 'bull';

import { EmailService } from './email.service';

export const EMAIL_QUEUE = 'email';

export interface PasswordResetJob {
  email: string;
  userName: string;
  resetLink: string;
}

export interface PasswordChangedJob {
  email: string;
  userName: string;
}

@Processor(EMAIL_QUEUE)
export class EmailProcessor {
  private readonly logger = new Logger(EmailProcessor.name);

  constructor(private readonly emailService: EmailService) {}

  @Process('password-reset')
  async handlePasswordReset(job: Job<PasswordResetJob>): Promise<void> {
    const { email, userName, resetLink } = job.data;
    this.logger.log(`Processing password-reset email job for ${email}`);
    await this.emailService.sendPasswordResetEmail(email, userName, resetLink);
  }

  @Process('password-changed')
  async handlePasswordChanged(job: Job<PasswordChangedJob>): Promise<void> {
    const { email, userName } = job.data;
    this.logger.log(`Processing password-changed email job for ${email}`);
    await this.emailService.sendPasswordChangedEmail(email, userName);
  }
}
