import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { selectUser } from '../../../state/auth/auth.selectors';
import * as AuthActions from '../../../state/auth/auth.actions';
import { take, firstValueFrom } from 'rxjs';
import { UserProvider } from '../data/user.provider';
import { AuthApiService } from '../../auth/provider/auth-api.service';
import Swal from 'sweetalert2';

// Local frontend representation of backend DTO (partial, writable fields)
interface UserDto {
  id?: number;
  firstName: string;
  lastName: string;
  email: string;
  role?: string;
  gender?: string | null;
  birthDate?: string | null; // ISO date string
  createdAt?: string;
  updatedAt?: string;
  deletedAt?: string;
}

// Payload type used when updating current user from the form
type UserUpdate = Partial<UserDto> & { password?: string };

@Component({
  selector: 'app-profile-edit',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile-edit.component.html',
  styleUrls: ['./profile-edit.component.scss']
})
export class ProfileEditComponent implements OnInit {
  // Minimal model for editing current user profile
  // unified full name input (client-side)
  fullName = '';
  email = '';
  birthDate?: string | null = null; // YYYY-MM-DD
  gender = '';
  userId?: number | string;
  isLoading = false;
  // Optional password change
  password = '';
  confirmPassword = '';

  genderOptions = [
    { value: '', label: 'Selecione' },
    { value: 'MALE', label: 'Masculino' },
    { value: 'FEMALE', label: 'Feminino' },
    { value: 'OTHER', label: 'Outro' }
  ];

  // Password change modal state
  showPasswordModal = false;
  currentPassword = '';
  newPassword = '';
  confirmNewPassword = '';
  changingPassword = false;

  constructor(
    private router: Router,
    private store: Store,
    private userProvider: UserProvider,
    private authService: AuthApiService
  ) {}
  ngOnInit(): void {
    // Prefill form with current user data (one-time)
    this.store
      .select(selectUser)
      .pipe(take(1))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .subscribe((user: any) => {
        if (!user) return;
        // Prefill a single fullName field by joining first and last name
        const first = user.firstName || '';
        const last = user.lastName || '';
        this.fullName = (first + (last ? ' ' + last : '')).trim();
        this.email = user.email || '';
        this.birthDate = user.birthDate
          ? new Date(user.birthDate).toISOString().slice(0, 10)
          : null;
        this.gender = user.gender || '';
        this.userId = user.id;
      });
  }

  save(form?: NgForm): void {
    if (form && !form.valid) {
      console.warn('Form inválido');
      return;
    }

    if (this.password && this.password !== this.confirmPassword) {
      console.warn('Senha e confirmação não conferem');
      return;
    }

    // Split fullName into firstName (first word) and lastName (rest)
    const names = (this.fullName || '').trim().split(/\s+/).filter(Boolean);
    if (names.length < 2) {
      console.warn('Informe nome e sobrenome');
      return;
    }

    const firstName = names.shift() || '';
    const lastName = names.join(' ') || '';

    const payload: UserUpdate = {
      firstName,
      lastName,
      email: this.email,
      birthDate: this.birthDate,
      gender: this.gender || null
    };

    if (this.password) {
      payload.password = this.password;
    }

    console.log('Salvar perfil (payload):', payload as UserDto);

    if (this.userId != null) {
      this.isLoading = true;
      Swal.fire({
        title: 'Salvando...',
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });
      this.userProvider.updateMe(payload).subscribe({
        next: (resp) => {
          this.isLoading = false;
          try {
            this.store.dispatch(AuthActions.updateUserSuccess({ user: resp }));
          } catch (e) {
            console.warn('Erro ao dispatch updateUserSuccess:', e);
          }
          Swal.close();
          Swal.fire({
            icon: 'success',
            title: 'Perfil atualizado',
            text: 'Seu perfil foi atualizado com sucesso.'
          }).then(() => this.router.navigate(['/home']));
        },
        error: (err) => {
          this.isLoading = false;
          Swal.close();
          const msg =
            err?.error?.message || err?.message || err?.statusText || 'Erro desconhecido';
          console.warn('Erro ao atualizar usuário:', err);
          Swal.fire({
            icon: 'error',
            title: 'Erro ao atualizar perfil',
            html: `<p>${msg}</p>`
          });
        }
      });
    } else {
      // fallback: no id available - optimistic update
      try {
        this.store.dispatch(AuthActions.updateUserSuccess({ user: payload }));
      } catch (e) {
        console.warn('Erro ao dispatch updateUserSuccess:', e);
      }
      Swal.fire({
        icon: 'success',
        title: 'Perfil atualizado',
        text: 'Seu perfil foi atualizado localmente.'
      }).then(() => this.router.navigate(['/home']));
    }
  }

  cancel(): void {
    try {
      this.router.navigate(['/home']);
    } catch (e) {
      console.warn('Erro ao cancelar edição do perfil:', e);
    }
  }

  private generateConfirmCode(len = 8): string {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
    let out = '';
    for (let i = 0; i < len; i++) {
      out += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return out;
  }

  openPasswordModal(): void {
    this.currentPassword = '';
    this.newPassword = '';
    this.confirmNewPassword = '';
    this.showPasswordModal = true;
  }

  closePasswordModal(): void {
    this.showPasswordModal = false;
    this.currentPassword = '';
    this.newPassword = '';
    this.confirmNewPassword = '';
  }

  async changePassword(): Promise<void> {
    if (!this.currentPassword || !this.newPassword || !this.confirmNewPassword) {
      Swal.fire({
        icon: 'warning',
        title: 'Atenção',
        text: 'Preencha todos os campos.'
      });
      return;
    }

    if (this.newPassword.length < 6) {
      Swal.fire({
        icon: 'warning',
        title: 'Atenção',
        text: 'A nova senha deve ter pelo menos 6 caracteres.'
      });
      return;
    }

    if (this.newPassword !== this.confirmNewPassword) {
      Swal.fire({
        icon: 'warning',
        title: 'Atenção',
        text: 'A nova senha e a confirmação não coincidem.'
      });
      return;
    }

    this.changingPassword = true;
    try {
      await firstValueFrom(this.authService.changePassword(this.currentPassword, this.newPassword));
      this.closePasswordModal();
      Swal.fire({
        icon: 'success',
        title: 'Sucesso!',
        text: 'Sua senha foi alterada com sucesso.'
      });
    } catch (error: any) {
      const message = error?.error?.message || 'Erro ao alterar senha. Verifique a senha atual.';
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: message
      });
    } finally {
      this.changingPassword = false;
    }
  }

  confirmAndDelete(): void {
    const code = this.generateConfirmCode(8);
    Swal.fire({
      title: 'Confirmar exclusão',
      html: `<p>Para confirmar a exclusão da sua conta, digite o código abaixo:</p><p style="font-weight:700;letter-spacing:1px">${code}</p>`,
      input: 'text',
      inputPlaceholder: 'Digite o código aqui',
      showCancelButton: true,
      confirmButtonText: 'Excluir conta',
      cancelButtonText: 'Cancelar',
      preConfirm: (value) => {
        if (!value || value !== code) {
          Swal.showValidationMessage('Código não confere');
          return false;
        }
        return true;
      }
    }).then((result) => {
      if (result.isConfirmed) {
        // proceed with delete
        this.isLoading = true;
        Swal.fire({
          title: 'Excluindo conta...',
          allowOutsideClick: false,
          didOpen: () => Swal.showLoading()
        });
        this.userProvider.deleteMe().subscribe({
          next: () => {
            this.isLoading = false;
            Swal.close();
            Swal.fire({
              icon: 'success',
              title: 'Conta excluída',
              text: 'Sua conta foi excluída com sucesso.'
            }).then(() => {
              try {
                this.store.dispatch(AuthActions.logout());
              } catch (e) {
                console.warn('Erro ao dispatch logout:', e);
              }
              this.router.navigate(['/auth/login']);
            });
          },
          error: (err) => {
            this.isLoading = false;
            Swal.close();
            const msg = err?.error?.message || err?.message || err?.statusText || 'Erro desconhecido';
            console.warn('Erro ao excluir usuário:', err);
            Swal.fire({
              icon: 'error',
              title: 'Erro ao excluir conta',
              html: `<p>${msg}</p>`
            });
          }
        });
      }
    });
  }
}
