export interface TableColumn {
  label: string;
  key: string;
  // 'img' will render a thumbnail using the cell value as an image URL
  format?: 'date' | 'boolean' | 'currency' | 'datetime' | 'img';
  colSpan?: number;
  className?: string;
}
