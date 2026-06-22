import { Injectable, Logger } from '@nestjs/common';
import { createHmac } from 'crypto';
import { PrismaService } from 'src/database/prisma/prisma.service';

// Entrega payloads de eventos aos webhooks ativos de uma empresa.
// Injetável por outros módulos (WebhooksModule é @Global e exporta este serviço).
@Injectable()
export class WebhookDispatchService {
  private readonly logger = new Logger(WebhookDispatchService.name);

  constructor(private readonly prisma: PrismaService) {}

  // Fire-and-forget: nunca lança para o chamador; falhas individuais são engolidas.
  async dispatch(companyId: number, event: string, payload: unknown): Promise<void> {
    try {
      const webhooks = await this.prisma.webhook.findMany({
        where: { companyId, active: true }
      });

      const targets = webhooks.filter((w) => {
        const events = w.events as string[] | null;
        // events null/vazio = escuta todos os eventos
        return !events || events.length === 0 || events.includes(event);
      });
      if (targets.length === 0) return;

      const body = JSON.stringify({
        event,
        payload,
        timestamp: new Date().toISOString()
      });

      await Promise.allSettled(
        targets.map((w) => this.deliver(w.url, w.secret, event, body))
      );
    } catch (err) {
      // Auditoria/entrega de webhook nunca deve quebrar a operação principal.
      this.logger.warn(`Falha ao despachar webhook '${event}': ${String(err)}`);
    }
  }

  private async deliver(
    url: string,
    secret: string | null,
    event: string,
    body: string
  ): Promise<void> {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Maestro-Event': event
      };
      if (secret) {
        const signature = createHmac('sha256', secret).update(body).digest('hex');
        headers['X-Maestro-Signature'] = `sha256=${signature}`;
      }
      await fetch(url, { method: 'POST', headers, body });
    } catch (err) {
      this.logger.warn(`Webhook ${url} falhou: ${String(err)}`);
    }
  }
}
