import type { ExceptionFilter, ArgumentsHost } from '@nestjs/common';
import { HttpException, HttpStatus, Logger, Catch } from '@nestjs/common';
import { HttpAdapterHost } from '@nestjs/core';

@Catch()
class AllExceptionsFilter implements ExceptionFilter {
  private logger = new Logger('ExceptionFilter');

  constructor(private readonly httpAdapterHost: HttpAdapterHost) {}

  extractChildrenMessages(errors: any[]): string[] {
    let messages: string[] = [];

    errors.map((error) => {
      error.children.map((children) => {
        if (children.children) {
          messages = [...messages, ...this.extractChildrenMessages(children.children)];
        }

        if (children.constraints) {
          Object.values(children.constraints).map((error: string) => {
            messages.push(error);
            return;
          });
        }

        messages.push(children as any as string);
      });
    });
    return messages;
  }

  extractMessages(exception: any) {
    let messages: string[] = [];
    (exception.messages || [exception.message] || ['Unknown server error']).map(
      (message: Record<string, any>) => {
        if (message.constraints) {
          Object.values(message.constraints).map((error: string) => {
            messages.push(error);
          });
        } else {
          if (message.children) {
            messages = [...messages, ...this.extractChildrenMessages(message.children)];
          } else {
            messages.push(message as any as string);
          }
        }
      }
    );

    return messages;
  }

  catch(exception: Error, host: ArgumentsHost): void {
    // In certain situations `httpAdapter` might not be available in the
    // constructor method, thus we should resolve it here.
    const { httpAdapter } = this.httpAdapterHost;

    if (process.env.NODE_ENV !== 'test') {
      if (exception.stack) {
        this.logger.error(exception.stack);
      }
    }

    const ctx = host.switchToHttp();
    const httpStatus =
      exception instanceof HttpException
        ? exception.getStatus()
        : HttpStatus.INTERNAL_SERVER_ERROR;

    const responseBody = {
      statusCode: httpStatus,
      timestamp: new Date().toISOString(),
      path: httpAdapter.getRequestUrl(ctx.getRequest()),
      messages: this.extractMessages(exception)
    };

    httpAdapter.reply(ctx.getResponse(), responseBody, httpStatus);
  }
}

export { AllExceptionsFilter };
