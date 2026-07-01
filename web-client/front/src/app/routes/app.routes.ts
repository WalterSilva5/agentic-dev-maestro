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
import { LabelsComponent } from '../pages/labels/labels.component';
import { AccessComponent } from '../pages/access/access.component';
import { MetricsComponent } from '../pages/metrics/metrics.component';
import { InviteComponent } from '../pages/invite/invite.component';
import { StudiesComponent } from '../pages/studies/studies.component';
import { StudyPlanComponent } from '../pages/studies/study-plan/study-plan.component';
import { AuthGuard } from '../permissions/auth.guard';
import { workspaceGuard } from '../permissions/workspace.guard';

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
  { path: 'invite/:token', component: InviteComponent },
  { path: RoutesEnum.SETTINGS, component: SettingsComponent, canActivate: [AuthGuard] },
  // Agentic Dev Maestro
  { path: RoutesEnum.DASHBOARD, component: DashboardComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.COMPANIES, component: CompaniesComponent, canActivate: [AuthGuard] },
  { path: RoutesEnum.PROJECTS, component: ProjectsComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.BOARD, component: BoardComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.TASK_DETAIL, component: TaskDetailComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.MEMBERS, component: MembersComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.API_KEYS, component: ApiKeysComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.LABELS, component: LabelsComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.ACCESS, component: AccessComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.METRICS, component: MetricsComponent, canActivate: [AuthGuard, workspaceGuard] },
  { path: RoutesEnum.DOWNLOADS, component: DownloadsComponent, canActivate: [AuthGuard] },
  { path: RoutesEnum.STUDIES, component: StudiesComponent, canActivate: [AuthGuard] },
  { path: RoutesEnum.STUDY_PLAN, component: StudyPlanComponent, canActivate: [AuthGuard] },
  { path: '**', component: NotFoundComponent }
];
