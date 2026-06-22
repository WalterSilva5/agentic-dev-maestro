import { InjectQueue } from '@nestjs/bull';
import { Injectable } from '@nestjs/common';
import { Queue } from 'bull';

import { EMAIL_QUEUE } from './email.processor';

@Injectable()
export class EmailQueue {
  constructor(@InjectQueue(EMAIL_QUEUE) private readonly queue: Queue) {}

  async enqueuePasswordReset(email: string, userName: string, resetLink: string): Promise<void> {
    await this.queue.add('password-reset', { email, userName, resetLink });
  }

  async enqueuePasswordChanged(email: string, userName: string): Promise<void> {
    await this.queue.add('password-changed', { email, userName });
  }
}
