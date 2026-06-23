import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import Swal from 'sweetalert2';
import { RouterModule, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { AppState } from '../../../state';
import { Store } from '@ngrx/store';
import * as AuthActions from '../../../../app/state/auth/auth.actions';
import {
  selectAuth,
} from '../../../../app/state/auth/auth.selectors';
import { AuthState } from '../../../state/auth/auth.models';
import { AuthApiHandler } from '../data-handler/auth-api.handler';
import { ConfigService } from '../../../services/config.service';
import { PlatformService } from '../../../services/platform.service';
import { WorkspaceService } from '../../../services/workspace.service';
import { TenantService } from '../../../services/tenant.service';
import { Browser } from '@capacitor/browser';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    CommonModule,
    RouterModule,
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  form: FormGroup = new FormGroup({});
  passwordFieldType = 'password';
  auth$: Observable<AuthState>;
  isLoading = false;
  apiUrl: string;

  constructor(
    private fb: FormBuilder,
    private store: Store<AppState>,
    private api: AuthApiHandler,
    private router: Router,
    private configService: ConfigService,
    private platformService: PlatformService,
    private workspaces: WorkspaceService,
    private tenant: TenantService,
  ) {
    this.auth$ = this.store.select(selectAuth);
    this.apiUrl = this.configService.apiUrl;
  }
  valueToIncrement = 5;

  updateAuthData(): void {}

  ngOnInit(): void {
    // Clear only persisted auth to reset the session.
    try {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth');
      }
    } catch (e) {
      console.warn('Could not remove persisted auth from localStorage', e);
    }

    this.store.dispatch(AuthActions.logout());
    this.tenant.clear();

    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(4)]],
    });
  }

  async onSubmit(): Promise<void> {
    if (this.form.valid) {
      this.isLoading = true;
      const { email, password } = this.form.value;
      const authResponse = await this.api.login({ email, password });
      this.isLoading = false;
      if (authResponse?.accessToken) {
        this.store.dispatch(AuthActions.loginSuccess({ auth: authResponse }));
        Swal.fire({
          title: 'Carregando...',
          timer: 500,
          timerProgressBar: true,
          didOpen: () => {
            Swal.showLoading();
          },
        });

        // Carrega os workspaces do usuário e auto-seleciona um ativo.
        try {
          await this.workspaces.refresh();
        } catch (e) {
          console.warn('Não foi possível carregar os workspaces após o login', e);
        }

        // Check for returnUrl to redirect after login
        const returnUrl = typeof window !== 'undefined' ? sessionStorage.getItem('returnUrl') : null;
        if (returnUrl) {
          sessionStorage.removeItem('returnUrl');
          this.router.navigateByUrl(returnUrl);
        } else {
          this.router.navigate(['/home']);
        }
      } else {
        this.showAlert('Usuário ou senha inválidos');
      }
    }
  }

  get openEyeIconPath(): string {
    return '/icons/General/Visible.svg';
  }

  get closeEyeIconPath(): string {
    return '/icons/General/Hidden.svg';
  }

  get googleLogoPath(): string {
    return '/icons/google.svg';
  }

  showAlert(message: string): void {
    Swal.fire({
      title: 'Alerta',
      html: `<p>${message}</p>`,
    });
  }

  togglePasswordVisibility(): void {
    this.passwordFieldType =
      this.passwordFieldType === 'password' ? 'text' : 'password';
  }

  async loginWithGoogle(): Promise<void> {
    const googleUrl = `${this.apiUrl}/auth/accounts/google/login/`;
    if (this.platformService.isNative) {
      await Browser.open({ url: googleUrl });
    } else {
      window.location.href = googleUrl;
    }
  }
}
