import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import Swal from 'sweetalert2';
import { AuthApiService } from '../provider/auth-api.service';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
  templateUrl: './forgot-password.component.html',
  styleUrls: ['./forgot-password.component.scss'],
})
export class ForgotPasswordComponent implements OnInit {
  form: FormGroup = new FormGroup({});
  isLoading = false;
  emailSent = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
  }

  async onSubmit(): Promise<void> {
    if (this.form.valid) {
      this.isLoading = true;
      try {
        const { email } = this.form.value;
        await firstValueFrom(this.authService.forgotPassword(email));
        this.emailSent = true;
        Swal.fire({
          icon: 'success',
          title: 'Email enviado!',
          text: 'Verifique sua caixa de entrada para redefinir sua senha.',
          confirmButtonColor: '#1DB954',
        });
      } catch (error: any) {
        Swal.fire({
          icon: 'info',
          title: 'Verificacao enviada',
          text: 'Se o email existir em nossa base, voce recebera instrucoes de recuperacao.',
          confirmButtonColor: '#1DB954',
        });
        this.emailSent = true;
      } finally {
        this.isLoading = false;
      }
    }
  }

  goBack(): void {
    this.router.navigate(['/auth/login']);
  }
}
