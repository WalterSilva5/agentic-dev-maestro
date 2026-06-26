import { Injectable, OnDestroy, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { AppState } from '../state';
import { selectAuth } from '../state/auth/auth.selectors';
import { Subscription, fromEvent, interval, merge, of } from 'rxjs';
import { distinctUntilChanged, filter, map, withLatestFrom, throttleTime, startWith, exhaustMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class CreditsSyncService implements OnDestroy {
  private readonly store: Store<AppState> = inject(Store);
  private sub?: Subscription;

  start(options?: { intervalMs?: number }): void {
    if (this.sub) return; // already started
    // Guard against server-side rendering where window/document are undefined
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }
    const intervalMs = options?.intervalMs ?? 60_000; // default: 60s

    const isAuth$ = this.store.select(selectAuth).pipe(
      map((a) => !!a?.accessToken),
      distinctUntilChanged()
    );

    const focus$ = fromEvent(window, 'focus');
    const visible$ = fromEvent(document, 'visibilitychange').pipe(
      filter(() => document.visibilityState === 'visible')
    );
    const timer$ = interval(intervalMs);

    const triggers$ = merge(of(0), focus$, visible$, timer$).pipe(
      // avoid spamming on bursts
      throttleTime(500, undefined, { leading: true, trailing: true }),
      startWith(0)
    );

    // subscribe to triggers and refresh when authenticated
    this.sub = triggers$.pipe(
      withLatestFrom(isAuth$),
      filter(([_, loggedIn]) => loggedIn),
      exhaustMap(() => {
        // TODO: implement actual refresh credits logic here
        return of(null);
      })
    ).subscribe();
  }

  stop(): void {
    this.sub?.unsubscribe();
    this.sub = undefined;
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
