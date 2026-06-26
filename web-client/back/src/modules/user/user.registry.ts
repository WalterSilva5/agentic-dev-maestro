import { Injectable } from '@nestjs/common';

@Injectable()
export class UserActivityRegistry {
  public readonly userLastActivity: Map<string, Date> = new Map();
  private readonly activityTimeout: number = 1;

  registerActivity(userId: string): void {
    this.userLastActivity.set(userId, new Date());
  }

  pruneInactiveUsers(): void {
    const now = new Date();
    for (const [userId, lastActivity] of this.userLastActivity.entries()) {
      if ((now.getTime() - lastActivity.getTime()) / (1000 * 60) > this.activityTimeout) {
        this.userLastActivity.delete(userId);
      }
    }
  }

  getLastActivity(userId: string): Date | undefined {
    return this.userLastActivity.get(userId);
  }
}
