import type { NestMiddleware } from '@nestjs/common';
import { Injectable, Logger } from '@nestjs/common';
import type { Request, Response, NextFunction } from 'express';

@Injectable()
export class HTTPLoggerMiddleware implements NestMiddleware {
  private logger = new Logger('HTTPLogger');

  parseArgs(start: number, end: number, args: Record<string, any>) {
    const message = Object.entries(args)
      .map(([key, value]) => `${key}=${value}`)
      .join(', ');

    this.logger.log(message + ` +${end - start}ms`);
  }

  use(request: Request, response: Response, next: NextFunction): void {
    const { method, baseUrl } = request;
    const start = Date.now();

    response.on('close', () => {
      const { statusCode } = response;
      const end = Date.now();
      this.parseArgs(start, end, {
        method: method,
        endpoint: baseUrl,
        status: statusCode
      });
    });

    next();
  }
}
