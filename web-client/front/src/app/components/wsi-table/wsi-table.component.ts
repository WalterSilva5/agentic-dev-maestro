// wsi-table.component.ts
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Meta } from '../../models/meta.type';
import { TableColumn } from './types/table-column.type';

@Component({
  selector: 'app-wsi-table',
  templateUrl: './wsi-table.component.html',
  styleUrls: ['./wsi-table.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule],
})
export class WsiTableComponent {
  @Input() data: any[] = [];
  @Input() meta: Meta | undefined;
  @Input() columns: TableColumn[] = [];
  @Input() showPagination: boolean = true;
  @Input() showFilter: boolean = true;
  @Input() showActions: boolean = true;
  @Input() activeActions: string[] = [];
  @Output() rowClick = new EventEmitter<any>();
  @Output() filterChange = new EventEmitter<string>();
  @Output() editClick = new EventEmitter<any>();
  @Output() deleteClick = new EventEmitter<any>();
  @Output() pageChange = new EventEmitter<number>();


  currentPage: number = 1;
  pageSize: number = 10;
  filterValue: string = '';

  get editIcon(): string {
    return '/icons/Design/Edit.svg';
  }

  get deleteIcon(): string {
    return '/icons/General/Trash.svg'
  }

  get displayedData(): any[] {
    let filteredData = this.data;
    if (this.filterValue.trim() !== '') {
      const filterText = this.filterValue.toLowerCase().trim();
      filteredData = filteredData.filter(row =>
        this.columns.some(column => {
          const cellValue = row[column.key];
          return cellValue !== undefined && cellValue.toString().toLowerCase().includes(filterText);
        })
      );
    }

    return filteredData;
  }

  get totalPages(): number {
    return this.meta?.lastPage || 1;
  }

  onRowClick(row: any) {
    this.rowClick.emit(row);
  }

  onEditClick(row: any, event: Event) {
    event.stopPropagation();
    this.editClick.emit(row);
  }

  onDeleteClick(row: any, event: Event) {
    event.stopPropagation();
    this.deleteClick.emit(row);
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.pageChange.emit(this.currentPage);
    }
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.pageChange.emit(this.currentPage);
    }
  }

  onFilterChange() {
    this.filterChange.emit(this.filterValue);
  }

  formatValue(value: any, format?: 'date' | 'boolean' | 'currency' | 'datetime' | 'img'): any {
    if (!format) {
      return value;
    }

    switch (format) {
      case 'date':
        return new Date(value).toLocaleDateString();
      case 'datetime':
        const date =new Date(value).toISOString().split('T')[0];
        const time = new Date(value).toISOString().split('T')[1].split('.')[0];
        return `${date} - ${time}`;
      case 'boolean':
        return value ? 'Sim' : 'Não';
      case 'currency':
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
      default:
        return value;
    }
  }

  // Substitui imagem quebrada por um placeholder discreto
  onImgError(event: Event) {
    const target = event.target as HTMLImageElement;
    // Um placeholder sutil (1x1 gif transparente) para não quebrar layout
    target.src = 'data:image/gif;base64,R0lGODlhAQABAAAAACw=';
    target.classList.add('wsi-thumb--error');
  }
}
