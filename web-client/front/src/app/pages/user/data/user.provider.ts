/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @angular-eslint/prefer-inject */
import { Injectable, Injector } from '@angular/core';
import { DataService } from '../../../modules/data-service/data.service';
import { PaginatedData } from '../../../models/paginated-data.type';
import { catchError, timeout } from 'rxjs/operators';
import { Observable, throwError } from 'rxjs';
import { PaginationFilters } from '../../../models/pagination-filters.type';
import { HttpErrorResponse } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class UserProvider extends DataService {
  endpoint = 'user';

  constructor(injector: Injector) {
    super(injector);
  }
  getMany(filters: PaginationFilters): Observable<PaginatedData<any>> {
    return this.getManyData<PaginatedData<any>>(`${this.endpoint}?${filters.search}`);
  }

  create(data: any): Observable<any> {
    console.log('Creating user: ', data);
    return this.postData<any>(data, `${this.endpoint}`);
  }

  delete(id: string): Observable<any> {
    console.log('Deleting user: ', id);
    return this.deleteData(id, `${this.endpoint}`);
  }

  getById(id: string): Observable<any> {
    return this.getOneData<any>(id, `${this.endpoint}`);
  }

  update(id: string, data: any): Observable<any> {
    console.log('Updating user: ', data);
    console.log('Updating user id: ', id);
    return this.updateData<any>(data, id, `${this.endpoint}`).pipe(
      timeout(5000),
      catchError((err: HttpErrorResponse) => {
        console.error('error updating user: ', err);
        return throwError(err);
      })
    );
  }


  updateMe(data: any): Observable<any> {
    console.log('Updating current user: ', data);
    return this.updateData<any>(data, "", `${this.endpoint}/me`).pipe(
      timeout(5000),
      catchError((err: HttpErrorResponse) => {
        console.error('error updating current user: ', err);
        return throwError(err);
      })
    );
  }

  deleteMe(): Observable<any> {
    console.log('Deleting current user');
    return this.deleteData("", `${this.endpoint}/me`).pipe(
      timeout(5000),
      catchError((err: HttpErrorResponse) => {
        console.error('error deleting current user: ', err);
        return throwError(err);
      })
    );
  }

  searchByEmail(email: string): Observable<any[]> {
    return this.getManyData<any[]>(`${this.endpoint}/search?email=${encodeURIComponent(email)}`).pipe(
      timeout(5000),
      catchError((err: HttpErrorResponse) => {
        console.error('error searching users: ', err);
        return throwError(err);
      })
    );
  }

  searchUsers(query: string): Observable<any[]> {
    return this.getManyData<any[]>(`${this.endpoint}/search?q=${encodeURIComponent(query)}`).pipe(
      timeout(5000),
      catchError((err: HttpErrorResponse) => {
        console.error('error searching users: ', err);
        return throwError(err);
      })
    );
  }
}
