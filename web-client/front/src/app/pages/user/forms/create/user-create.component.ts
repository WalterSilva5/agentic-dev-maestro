import { Component, OnInit } from '@angular/core';
import { UserProcessor } from '../../data/user.processor';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { CommonModule } from '@angular/common';
import Swal from 'sweetalert2';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-user-create',
  standalone: true,
  templateUrl: './user-create.component.html',
  styleUrls: ['./user-create.component.scss'],
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
})
export class UserCreateComponent implements OnInit {
  form: FormGroup = new FormGroup({});

  constructor(
    private fb: FormBuilder,
    private api: UserProcessor,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required],
      role: ['USER', Validators.required],
    });
  }

  onSubmit() {
    if (this.form.valid) {
      // Show loading indicator
      Swal.fire({
        title: 'Criando usuário...',
        html: 'Por favor, aguarde.',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });

      this.api
        .create(this.form.value)
        .then((res) => {
          console.log('User created: ', res);
          Swal.fire({
            icon: 'success',
            title: 'Usuário criado com sucesso!',
            text: 'O usuário foi criado com sucesso.',
            showConfirmButton: true,
          }).then(() => {
            this.router.navigate(['/user']);
          });
        })
        .catch((err) => {
          console.error('Error creating user: ', err);
          Swal.fire({
            icon: 'error',
            title: 'Erro ao criar usuário',
            text: 'Ocorreu um erro ao criar o usuário. Por favor, tente novamente.',
            showConfirmButton: true,
          });
        });
    } else {
      Swal.fire({
        icon: 'warning',
        title: 'Formulário inválido',
        text: 'Por favor, preencha todos os campos obrigatórios.',
        showConfirmButton: true,
      });
    }
  }

  getById(id: string) {
    this.api.getById(id).then((res) => {
      console.log('User by ID: ', res);
    });
  }
}
