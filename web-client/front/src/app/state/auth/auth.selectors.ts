import { createSelector, createFeatureSelector } from '@ngrx/store';
import { AuthState } from './auth.models';

export const selectAuthState = createFeatureSelector<AuthState>('auth');

export const selectUser = createSelector(
  selectAuthState,
  (state) => state.user
);

export const selectIsLoggedIn = createSelector(
  selectAuthState,
  (state) => state.isAuthenticated
);

export const selectUserRole = createSelector(
  selectAuthState,
  (state) => state.user?.role
);

export const selectAuthError = createSelector(
  selectAuthState,
  (state) => state.error
);

export const selectAuth = createSelector(
  selectAuthState,
  (state) => state
);

export const selectAuthToken = createSelector(
  selectAuthState,
  (state) => state.accessToken
);

export const selectRefreshToken = createSelector(
  selectAuthState,
  (state) => state.refreshToken
);

