import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable, map } from 'rxjs';
import { AppState } from '../../state';
import { selectIsLoggedIn, selectAuth } from '../../state/auth/auth.selectors';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  isLoggedIn = false;
  userName$!: Observable<string>;
  userBalance$!: Observable<number>;

  constructor(
    private router: Router,
    private store: Store<AppState>
  ) {}

  ngOnInit(): void {
    this.store.select(selectIsLoggedIn).subscribe((isLoggedIn) => {
      this.isLoggedIn = isLoggedIn;
    });

    const auth$ = this.store.select(selectAuth);
    this.userName$ = auth$.pipe(
      map((a) => `${a?.user?.firstName ?? ''} ${a?.user?.lastName ?? ''}`.trim())
    );
    this.userBalance$ = auth$.pipe(map((a) => a?.user?.creditAccount?.balance ?? 0));
  }

  goToLogin(): void {
    this.router.navigate(['/auth/login']);
  }

  goToProfile(): void {
    this.router.navigate(['/user/profile']);
  }
}
