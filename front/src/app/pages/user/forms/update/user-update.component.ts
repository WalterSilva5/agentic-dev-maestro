import { Component, OnInit, inject } from '@angular/core';
import { UserProcessor } from '../../data/user.processor';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { CreditDataService } from '../../../credit/data/credit-data.service';
import { CreditTransactionDataService } from '../../../credit/data/credit-transaction-data.service';
import { PaginatedData } from '../../../../models/paginated-data.type';
import { CreditTransaction, CreditTransactionFilters } from '../../../credit/api/credit-transaction-api.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-user-update',
  standalone: true,
  templateUrl: './user-update.component.html',
  styleUrl: './user-update.component.scss',
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
})
export class UserUpdateComponent implements OnInit {
  id: string | null = null;
  userForm: FormGroup;
  creditForm: FormGroup;
  creditResult: Record<string, unknown> | null = null;
  currentCredits = 0;
  transactions: PaginatedData<CreditTransaction> | null = null;
  transactionFilters!: CreditTransactionFilters; // definido após obter o id

  private api = inject(UserProcessor);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);
  private creditSvc = inject(CreditDataService);
  private transactionSvc = inject(CreditTransactionDataService);

  constructor() {
    this.userForm = this.fb.group({
      id: [''],
      firstName: [''],
      lastName: [''],
      email: [''],
      role: [''],
    });
    this.creditForm = this.fb.group({
      amount: [0],
    });
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      this.id = params.get('id');
      if (this.id) {
        this.fetchData(this.id);
      }
    });
  }

  async fetchData(id: string) {
    console.log('USER COMPONENT UPDATE ID: ', id);
    const user = await this.api.getById(id);
    console.log('USER COMPONENT UPDATE USER: ', user);
    this.userForm.patchValue(user);
    this.currentCredits = user?.creditAccount?.balance || 0;

  // Inicializa os filtros já com o userId obrigatório
  this.transactionFilters = { page: 1, limit: 10, userId: Number(id) };

    await this.loadTransactions();
  }

  async loadTransactions() {
    if (this.id) {
      try {
        // Garantir que userId está sempre presente
        if (!this.transactionFilters?.userId) {
          this.transactionFilters = {
            page: this.transactionFilters?.page ?? 1,
            limit: this.transactionFilters?.limit ?? 10,
            userId: Number(this.id)
          };
        }
        console.log('Loading transactions with filters:', this.transactionFilters);
        const allTransactions = await this.transactionSvc.getUserTransactions(this.transactionFilters);
        this.transactions = allTransactions;
      } catch (err) {
        console.error('Error loading transactions:', err);
        this.transactions = null;
      }
    }
  }

  async onSubmit() {
    if (this.userForm.valid) {
      console.log('Form data before submit:', this.userForm.value);

      // Show loading indicator
      Swal.fire({
        title: 'Atualizando usuário...',
        html: 'Por favor, aguarde.',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });

      try {
        const updatedUser = this.userForm.value;
        console.log('Calling updateUser with:', updatedUser.id, updatedUser);
        const result = await this.api.updateUser(updatedUser.id, updatedUser);
        console.log('User updated successfully:', result);

        Swal.fire({
          icon: 'success',
          title: 'Usuário atualizado com sucesso!',
          text: 'Os dados do usuário foram atualizados.',
          showConfirmButton: true,
        });
      } catch (error) {
        console.error('Error updating user:', error);
        Swal.fire({
          icon: 'error',
          title: 'Erro ao atualizar usuário',
          text: 'Ocorreu um erro ao atualizar os dados do usuário. Por favor, tente novamente.',
          showConfirmButton: true,
        });
      }
    } else {
      console.log('Form is invalid:', this.userForm.errors);
      Swal.fire({
        icon: 'warning',
        title: 'Formulário inválido',
        text: 'Por favor, preencha todos os campos obrigatórios.',
        showConfirmButton: true,
      });
    }
  }

  async addCredit() {
    if (this.creditForm.valid && this.id) {
      // Show loading indicator
      Swal.fire({
        title: 'Adicionando créditos...',
        html: 'Por favor, aguarde.',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });

      try {
        const { amount } = this.creditForm.value;
        this.creditResult = await this.creditSvc.addCredit(Number(this.id), Number(amount));

        // Atualizar saldo atual após operação
        if (this.creditResult) {
          this.currentCredits += Number(amount);
          // Recarregar transações para mostrar a nova transação
          await this.loadTransactions();

          Swal.fire({
            icon: 'success',
            title: 'Créditos adicionados com sucesso!',
            text: `${amount} créditos foram adicionados à conta do usuário.`,
            showConfirmButton: true,
          });

          // Reset form
          this.creditForm.patchValue({ amount: 0 });
        }
      } catch (error) {
        console.error('Error adding credits:', error);
        Swal.fire({
          icon: 'error',
          title: 'Erro ao adicionar créditos',
          text: 'Ocorreu um erro ao adicionar créditos. Por favor, tente novamente.',
          showConfirmButton: true,
        });
      }
    } else {
      Swal.fire({
        icon: 'warning',
        title: 'Dados inválidos',
        text: 'Por favor, insira um valor válido para os créditos.',
        showConfirmButton: true,
      });
    }
  }

  async subtractCredit() {
    if (this.creditForm.valid && this.id) {
      // Show loading indicator
      Swal.fire({
        title: 'Subtraindo créditos...',
        html: 'Por favor, aguarde.',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });

      try {
        const { amount } = this.creditForm.value;
        this.creditResult = await this.creditSvc.subtractCredit(Number(this.id), Number(amount));

        // Atualizar saldo atual após operação
        if (this.creditResult) {
          this.currentCredits -= Number(amount);
          // Recarregar transações para mostrar a nova transação
          await this.loadTransactions();

          Swal.fire({
            icon: 'success',
            title: 'Créditos subtraídos com sucesso!',
            text: `${amount} créditos foram subtraídos da conta do usuário.`,
            showConfirmButton: true,
          });

          // Reset form
          this.creditForm.patchValue({ amount: 0 });
        }
      } catch (error) {
        console.error('Error subtracting credits:', error);
        Swal.fire({
          icon: 'error',
          title: 'Erro ao subtrair créditos',
          text: 'Ocorreu um erro ao subtrair créditos. Por favor, tente novamente.',
          showConfirmButton: true,
        });
      }
    } else {
      Swal.fire({
        icon: 'warning',
        title: 'Dados inválidos',
        text: 'Por favor, insira um valor válido para os créditos.',
        showConfirmButton: true,
      });
    }
  }

  async changePage(page: number) {
    if (page >= 1 && page <= (this.transactions?.meta?.lastPage || 1)) {
      this.transactionFilters.page = page;
      await this.loadTransactions();
    }
  }

  getPageNumbers(): number[] {
    if (!this.transactions?.meta) return [];

    const current = this.transactions.meta.currentPage;
    const total = this.transactions.meta.lastPage;
    const pages: number[] = [];

    // Mostrar no máximo 5 páginas
    let start = Math.max(1, current - 2);
    let end = Math.min(total, current + 2);

    // Ajustar se estiver no início ou fim
    if (end - start < 4) {
      if (start === 1) {
        end = Math.min(total, start + 4);
      } else if (end === total) {
        start = Math.max(1, end - 4);
      }
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  }

  getMinValue(a: number, b: number): number {
    return Math.min(a, b);
  }
}
