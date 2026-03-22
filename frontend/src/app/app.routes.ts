import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./presentation/pages/dashboard/dashboard.component').then(
        (m) => m.DashboardComponent,
      ),
  },
  {
    path: 'nlp',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./presentation/pages/nlp-parse/nlp-parse.component').then(
        (m) => m.NlpParseComponent,
      ),
  },
  {
    path: 'detour',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./presentation/pages/detour-check/detour-check.component').then(
        (m) => m.DetourCheckComponent,
      ),
  },
  {
    path: 'route',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./presentation/pages/route-optimizer/route-optimizer.component').then(
        (m) => m.RouteOptimizerComponent,
      ),
  },
  {
    path: 'prices',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./presentation/pages/price-overview/price-overview.component').then(
        (m) => m.PriceOverviewComponent,
      ),
  },
  { path: '**', redirectTo: 'dashboard' },
];
