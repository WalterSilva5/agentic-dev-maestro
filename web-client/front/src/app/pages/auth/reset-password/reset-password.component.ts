import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import Swal from 'sweetalert2';
import { AuthApiService } from '../provider/auth-api.service';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.scss'],
})
export class ResetPasswordComponent implements OnInit {
  form: FormGroup = new FormGroup({});
  isLoading = false;
  isValidating = true;
  isTokenValid = false;
  passwordReset = false;
  token = '';
  email = '';
  passwordFieldType = 'password';
  confirmPasswordFieldType = 'password';

  constructor(
    private fb: FormBuilder,
    private authService: AuthApiService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  async ngOnInit(): Promise<void> {
    this.form = this.fb.group({
      newPassword: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
    }, { validators: this.passwordMatchValidator });

    // Get token from URL
    this.token = this.route.snapshot.queryParamMap.get('token') || '';

    if (!this.token) {
      this.isValidating = false;
      this.isTokenValid = false;
      return;
    }

    // Validate token
    try {
      const result = await firstValueFrom(this.authService.validateResetToken(this.token));
      this.isTokenValid = result.valid;
      this.email = result.email || '';
    } catch (error) {
      this.isTokenValid = false;
    } finally {
      this.isValidating = false;
    }
  }

  passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
    const password = control.get('newPassword');
    const confirmPassword = control.get('confirmPassword');

    if (password && confirmPassword && password.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    return null;
  }

  async onSubmit(): Promise<void> {
    if (this.form.valid && this.token) {
      this.isLoading = true;
      try {
        const { newPassword } = this.form.value;
        await firstValueFrom(this.authService.resetPassword(this.token, newPassword));
        this.passwordReset = true;
        Swal.fire({
          icon: 'success',
          title: 'Senha alterada!',
          text: 'Sua senha foi redefinida com sucesso. Faca login com sua nova senha.',
          confirmButtonColor: '#1DB954',
        });
      } catch (error: any) {
        const message = error?.error?.message || 'Erro ao redefinir senha. Tente novamente.';
        Swal.fire({
          icon: 'error',
          title: 'Erro',
          text: message,
          confirmButtonColor: '#ef4444',
        });
      } finally {
        this.isLoading = false;
      }
    }
  }

  togglePasswordVisibility(field: 'password' | 'confirm'): void {
    if (field === 'password') {
      this.passwordFieldType = this.passwordFieldType === 'password' ? 'text' : 'password';
    } else {
      this.confirmPasswordFieldType = this.confirmPasswordFieldType === 'password' ? 'text' : 'password';
    }
  }

  goToLogin(): void {
    this.router.navigate(['/auth/login']);
  }

  goToForgotPassword(): void {
    this.router.navigate(['/auth/forgot-password']);
  }
}
