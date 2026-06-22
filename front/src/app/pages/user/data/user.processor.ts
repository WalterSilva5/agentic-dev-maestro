import { Injectable } from '@angular/core';
import { PaginatedData } from '../../../models/paginated-data.type';
import { catchError, timeout } from 'rxjs/operators';
import { PaginationFilters } from '../../../models/pagination-filters.type';
import { UserProvider } from './user.provider';
import { of, throwError, firstValueFrom } from 'rxjs';
import Swal from 'sweetalert2';

@Injectable({
  providedIn: 'root',
})
export class UserProcessor {
  constructor(private api: UserProvider) {}

  async getMany(filters: PaginationFilters): Promise<PaginatedData<any>> {
    return firstValueFrom(
      this.api.getMany(filters).pipe(
        timeout(5000),
        catchError((err) => {
          console.error('error fetching data: ', err);
          return throwError(err);
        })
      )
    );
  }

  async create(data: any): Promise<any> {
    console.log('creating data: ', data);
    return firstValueFrom(
      this.api.create(data).pipe(
        timeout(5000),
        catchError((err) => {
          console.error('error creating data: ', err);
          return throwError(err);
        })
      )
    );
  }

  async delete(id: string): Promise<any> {
    console.log('deleting data: ', id);
    try {
      const result = await Swal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Yes, delete it!',
      });

      if (result.isConfirmed) {
        const response = await firstValueFrom(
          this.api.delete(id).pipe(
            timeout(5000),
            catchError((err) => {
              console.error('error deleting data: ', err);
              return throwError(err);
            })
          )
        );
        Swal.fire('Deleted!', 'Your file has been deleted.', 'success').then(
          () => {
            location.reload();
          }
        );
        return response;
      } else {
        Swal.fire('Cancelled', 'Your file is safe :)', 'error');
        return of(null);
      }
    } catch (err) {
      console.error('error deleting data: ', err);
      Swal.fire('Error!', 'There was an error deleting the data.', 'error');
      return throwError(err);
    }
  }

  async getById(id: string): Promise<any> {
    console.log('fetching data by id: ', id);
    return firstValueFrom(
      this.api.getById(id).pipe(
        timeout(5000),
        catchError((err) => {
          console.error('error fetching data by id: ', err);
          return throwError(err);
        })
      )
    );
  }

  async updateUser(id: string, data: any): Promise<any> {
    console.log('updating user: ', data);
    return firstValueFrom(
      this.api.update(id, data).pipe(
        timeout(5000),
        catchError((err) => {
          console.error('error updating user: ', err);
          return throwError(err);
        })
      )
    );
  }
}
