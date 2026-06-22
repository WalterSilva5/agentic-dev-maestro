import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import Swal from 'sweetalert2';
import { ConfigService } from '../../../services/config.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
})
export class RegisterComponent implements OnInit {
  form: FormGroup = new FormGroup({});
  passwordFieldType = 'password';
  confirmPasswordFieldType = 'password';
  isLoading = false;
  openEyeIconPath = '/icons/Navigation/eye.svg';
  closeEyeIconPath = '/icons/Navigation/eye-off.svg';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private configService: ConfigService
  ) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      fullName: ['', [Validators.required, Validators.minLength(5)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
    }, { validators: this.passwordMatchValidator });
  }

  passwordMatchValidator(group: FormGroup): Record<string, boolean> | null {
    const password = group.get('password')?.value;
    const confirmPassword = group.get('confirmPassword')?.value;

    if (password && confirmPassword && password !== confirmPassword) {
      group.get('confirmPassword')?.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    return null;
  }

  togglePasswordVisibility(): void {
    this.passwordFieldType = this.passwordFieldType === 'password' ? 'text' : 'password';
  }

  toggleConfirmPasswordVisibility(): void {
    this.confirmPasswordFieldType = this.confirmPasswordFieldType === 'password' ? 'text' : 'password';
  }

  async onSubmit(): Promise<void> {
    if (this.form.invalid) {
      return;
    }

    this.isLoading = true;

    try {
      const fullName = this.form.value.fullName.trim();
      const nameParts = fullName.split(' ');
      const firstName = nameParts[0];
      const lastName = nameParts.slice(1).join(' ') || firstName; // Se não houver sobrenome, usa o primeiro nome

      const payload = {
        firstName,
        lastName,
        email: this.form.value.email.trim().toLowerCase(),
        password: this.form.value.password,
      };

      const response = await fetch(`${this.configService.apiUrl}/user/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = Array.isArray(error.message)
          ? error.message.join(', ')
          : error.message || 'Erro ao registrar';

        Swal.fire({
          icon: 'error',
          title: 'Erro no Cadastro',
          text: errorMessage,
          confirmButtonText: 'OK',
        });
        return;
      }

      const _user = await response.json();

      Swal.fire({
        icon: 'success',
        title: 'Cadastro Realizado!',
        text: 'Sua conta foi criada com sucesso. Você será redirecionado para o login.',
        confirmButtonText: 'OK',
      }).then(() => {
        this.router.navigate(['/auth/login']);
      });
    } catch (error) {
      console.error('Erro ao registrar:', error);
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: 'Ocorreu um erro ao tentar registrar. Tente novamente.',
        confirmButtonText: 'OK',
      });
    } finally {
      this.isLoading = false;
    }
  }

  navigateToLogin(): void {
    this.router.navigate(['/auth/login']);
  }
}
