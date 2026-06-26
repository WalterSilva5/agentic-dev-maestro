import { BadRequestException } from '@nestjs/common';

interface ValidationError {
  target?: Record<string, unknown>;
  property: string;
  value?: unknown;
  constraints?: Record<string, string>;
  children?: ValidationError[];
  contexts?: Record<string, unknown>;
}

export class AppException extends BadRequestException {
  messages: ValidationError[];
  name: string;
  message: string;

  constructor(messages: ValidationError[]) {
    super(messages);
    this.messages = messages;
    this.name = 'AppException';
    this.message = this.formatValidationMessage(messages);
  }

  private formatValidationMessage(messages: ValidationError[]): string {
    if (!messages || !Array.isArray(messages)) {
      return 'Validation error occurred';
    }

    const errorMessages = messages
      .map((error: ValidationError) => {
        if (error.constraints) {
          return Object.values(error.constraints).join(', ');
        }
        return error.property
          ? `Invalid value for ${error.property}`
          : 'Unknown validation error';
      })
      .filter((msg: string) => msg.length > 0);

    return errorMessages.length > 0
      ? errorMessages.join('; ')
      : 'Validation error occurred';
  }
}
