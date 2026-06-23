import { Routes } from '@angular/router';
import { RoutesEnum } from './routes.enum';
import { HomeComponent } from '../pages/home/home.component';
import { UserComponent } from '../pages/user/user.component';
import { UserCreateComponent } from '../pages/user/forms/create/user-create.component';
import { UserUpdateComponent } from '../pages/user/forms/update/user-update.component';
import { ProfileEditComponent } from '../pages/user/profile-edit/profile-edit.component';
import { LoginComponent } from '../pages/auth/login/login.component';
import { RegisterComponent } from '../pages/auth/register/register.component';
import { GoogleCallbackComponent } from '../pages/auth/callback/callback.component';
import { ForgotPasswordComponent } from '../pages/auth/forgot-password/forgot-password.component';
import { ResetPasswordComponent } from '../pages/auth/reset-password/reset-password.component';
import { SettingsComponent } from '../pages/settings/settings.component';
import { NotFoundComponent } from '../pages/not-found/not-found.component';
// Agentic Dev Maestro
import { DashboardComponent } from '../pages/dashboard/dashboard.component';
import { CompaniesComponent } from '../pages/companies/companies.component';
import { ProjectsComponent } from '../pages/projects/projects.component';
import { BoardComponent } from '../pages/board/board.component';
import { TaskDetailComponent } from '../pages/task-detail/task-detail.component';
import { MembersComponent } from '../pages/members/members.component';
import { ApiKeysComponent } from '../pages/api-keys/api-keys.component';
import { DownloadsComponent } from '../pages/downloads/downloads.component';

export const routes: Routes = [
  { path: RoutesEnum.HOME, component: HomeComponent },
  { path: RoutesEnum.HOME_DEFAULT, component: HomeComponent },
  { path: RoutesEnum.USER, component: UserComponent },
  { path: RoutesEnum.USER_CREATE, component: UserCreateComponent },
  { path: RoutesEnum.USER_UPDATE, component: UserUpdateComponent },
  { path: RoutesEnum.USER_PROFILE, component: ProfileEditComponent },
  { path: RoutesEnum.LOGIN, component: LoginComponent },
  { path: 'auth/register', component: RegisterComponent },
  { path: 'auth/forgot-password', component: ForgotPasswordComponent },
  { path: 'auth/reset-password', component: ResetPasswordComponent },
  { path: RoutesEnum.GOOGLE_CALLBACK, component: GoogleCallbackComponent },
  { path: RoutesEnum.SETTINGS, component: SettingsComponent },
  // Agentic Dev Maestro
  { path: RoutesEnum.DASHBOARD, component: DashboardComponent },
  { path: RoutesEnum.COMPANIES, component: CompaniesComponent },
  { path: RoutesEnum.PROJECTS, component: ProjectsComponent },
  { path: RoutesEnum.BOARD, component: BoardComponent },
  { path: RoutesEnum.TASK_DETAIL, component: TaskDetailComponent },
  { path: RoutesEnum.MEMBERS, component: MembersComponent },
  { path: RoutesEnum.API_KEYS, component: ApiKeysComponent },
  { path: RoutesEnum.DOWNLOADS, component: DownloadsComponent },
  { path: '**', component: NotFoundComponent }
];
