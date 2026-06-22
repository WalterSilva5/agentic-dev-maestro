import { createAction, props } from '@ngrx/store';
import { AuthState } from './auth.models';

export enum AuthActionTypes {
  Login = '[Auth] Login',
  LoginSuccess = '[Auth] Login Success',
  LoginFailure = '[Auth] Login Failure',
  Logout = '[Auth] Logout',
  UpdateUserSuccess = '[Auth] Update User Success',
  RefreshToken = '[Auth] Refresh Token',
  RefreshTokenSuccess = '[Auth] Refresh Token Success',
  RefreshTokenFailure = '[Auth] Refresh Token Failure',
}


export const loginSuccess = createAction(
  AuthActionTypes.LoginSuccess,
  props<{ auth: AuthState }>()
);

export const updateUserSuccess = createAction(
  AuthActionTypes.UpdateUserSuccess,
  props<{ user: any }>()
);

export const logout = createAction(AuthActionTypes.Logout);

export const loginFailure = createAction(
  AuthActionTypes.LoginFailure,
  props<{ error: any }>()
);

export const refreshToken = createAction(
  AuthActionTypes.RefreshToken,
  props<{ refreshToken: string }>()
);

export const refreshTokenSuccess = createAction(
  AuthActionTypes.RefreshTokenSuccess,
  props<{ auth: AuthState }>()
);

export const refreshTokenFailure = createAction(
  AuthActionTypes.RefreshTokenFailure,
  props<{ error: any }>()
);

