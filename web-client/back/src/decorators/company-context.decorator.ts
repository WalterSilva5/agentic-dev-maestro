import type { ExecutionContext } from '@nestjs/common';
import { BadRequestException, createParamDecorator } from '@nestjs/common';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';

// Extrai o contexto de empresa preenchido pelo ApiAccessGuard.
export const CompanyContext = createParamDecorator(
  (_data: unknown, context: ExecutionContext): ICompanyContext => {
    const req = context.switchToHttp().getRequest<{ companyContext?: ICompanyContext }>();
    if (!req.companyContext) {
      throw new BadRequestException(
        'Contexto de empresa ausente: use uma API key ou envie o header X-Company-Id.'
      );
    }
    return req.companyContext;
  }
);
