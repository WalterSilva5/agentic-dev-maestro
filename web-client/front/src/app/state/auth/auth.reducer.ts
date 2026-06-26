import { createReducer, createSelector, on } from '@ngrx/store';
import { loginSuccess, loginFailure, logout, updateUserSuccess, refreshTokenSuccess, refreshTokenFailure } from './auth.actions';
import { AuthState, initialAuthState } from './auth.models';

const EMPTY_AUTH_STATE: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  user: null,
  error: null,
};
import { AppState } from '../index';

// Helper to safely persist auth only in the browser
function persistAuth(auth: Partial<AuthState>) {
  if (typeof window === 'undefined') return; // SSR safeguard
  try {
    window.localStorage.setItem('auth', JSON.stringify(auth));
  } catch (e) {
    // Swallow storage errors (e.g. quota, privacy mode)
    console.warn('Could not persist auth to localStorage', e);
  }
}

function removePersistedAuth() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem('auth');
  } catch (e) {
    console.warn('Could not remove auth from localStorage', e);
  }
}

export const authReducer = createReducer(
  initialAuthState,
  on(loginSuccess, (state, { auth }) => {
    // Persist minimal auth info (tokens + user). Avoid persisting error flags.
    persistAuth({
      accessToken: auth.accessToken,
      refreshToken: auth.refreshToken,
      user: auth.user,
      isAuthenticated: true,
      error: null,
    });
    return {
      ...state,
      ...auth,
      isAuthenticated: true,
      error: null,
    };
  }),
  on(updateUserSuccess, (state, { user }) => {
    // Atualiza apenas os dados do usuário, mantendo tokens
    const updatedState = {
      ...state,
      user: {
        ...state.user,
        ...user,
      },
    };
    // Persiste os dados atualizados
    persistAuth({
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
      user: updatedState.user,
      isAuthenticated: true,
      error: null,
    });
    return updatedState;
  }),
  on(refreshTokenSuccess, (state, { auth }) => {
    // TODO: Atualizar o estado com novos tokens e usuário após refresh bem-sucedido
    persistAuth({
      accessToken: auth.accessToken,
      refreshToken: auth.refreshToken,
      user: auth.user,
      isAuthenticated: true,
      error: null,
    });
    return {
      ...state,
      ...auth,
      isAuthenticated: true,
      error: null,
    };
  }),
  on(loginFailure, (state, { error }) => ({
    ...state,
    error,
  })),
  on(refreshTokenFailure, (state, { error }) => {
    removePersistedAuth();
    return {
      ...EMPTY_AUTH_STATE,
      error,
    };
  }),
  on(logout, (state) => {
    removePersistedAuth();
    return EMPTY_AUTH_STATE;
  })
);

// Selectors
export const selectAuthState = (state: AppState) => state.auth;

export const selectIsAuthenticated = createSelector(
  selectAuthState,
  (state: AuthState) => state.isAuthenticated
);

export const selectUser = createSelector(
  selectAuthState,
  (state: AuthState) => state.user
);

export const selectError = createSelector(
  selectAuthState,
  (state: AuthState) => state.error
);

export const selectAccessToken = createSelector(
  selectAuthState,
  (state: AuthState) => state.accessToken
);
