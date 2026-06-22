import { Component, OnInit } from '@angular/core';
import { WsiTableComponent } from '../../components/wsi-table/wsi-table.component';
import { TableColumn } from '../../components/wsi-table/types/table-column.type';
import { PaginationFilters } from '../../models/pagination-filters.type';
import { UserProcessor } from './data/user.processor';
import PaginatedData from '../../models/paginated-data.type';
import Meta from '../../models/meta.type';
import { Router } from '@angular/router';

@Component({
  selector: 'app-user',
  standalone: true,
  imports: [WsiTableComponent],
  templateUrl: './user.component.html',
  styleUrl: './user.component.scss',
})
export class UserComponent implements OnInit {
  columns: TableColumn[] = [
    { label: 'ID', key: 'id' },
    { label: 'Nome', key: 'firstName' },
    { label: 'Perfil', key: 'role' },
    { label: 'Email', key: 'email' },
  ];

  data: PaginatedData<any> = new PaginatedData();
  meta: Meta = new Meta();

  constructor(private api: UserProcessor, protected router: Router) {}
  ngOnInit(): void {
    this.fetchData({ search: '' });
  }

  async fetchData(filters: PaginationFilters) {
    const data = await this.api.getMany(filters);
    console.log('user paginated: ', data);
    this.data = data;
  }

  handleEditClick(event: any) {
    this.router.navigate(['/user/update', { id: event?.id }]);
  }

  handleDeleteClick(event: any) {
    this.deleteUser(`${event?.id}`);
  }

  async deleteUser(id: string) {
    const deleteResposne = await this.api.delete(id);
    console.log('deleteResposne', deleteResposne);
  }

  handleFilterChange(event: any) {
    console.log('handleFilterChange', event);
  }

  handleRowClick(event: any) {
    console.log('handleRowClick', event);
  }

  handlePageChange(event: any) {
    console.log('handlePageChange', event);
  }
}
