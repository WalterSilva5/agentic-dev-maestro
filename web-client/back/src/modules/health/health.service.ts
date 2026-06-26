import { Injectable } from '@nestjs/common';

@Injectable()
export class HealthService {
  constructor() {}

  async getStatus(): Promise<any> {
    return { status: 'ok' };
  }
}
