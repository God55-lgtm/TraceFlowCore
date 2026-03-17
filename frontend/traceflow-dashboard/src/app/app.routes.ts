import { Routes } from '@angular/router';
import { LoginComponent } from './features/login/login.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { TraceListComponent } from './features/trace-list/trace-list.component';
import { TraceDetailComponent } from './features/trace-detail/trace-detail.component';
import { AuthGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: 'traces', component: TraceListComponent, canActivate: [AuthGuard] },
  { path: 'traces/:id', component: TraceDetailComponent, canActivate: [AuthGuard] },
  { path: '**', redirectTo: '/dashboard' }
];