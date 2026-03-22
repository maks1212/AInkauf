import { inject } from '@angular/core';
import { CanActivateFn } from '@angular/router';
import { AuthService } from '@auth0/auth0-angular';
import { map, take } from 'rxjs';

import { environment } from '../../../environments/environment';

const isAuth0Configured =
  environment.auth0.domain !== 'YOUR_AUTH0_DOMAIN.auth0.com' &&
  environment.auth0.clientId !== 'YOUR_AUTH0_CLIENT_ID';

export const authGuard: CanActivateFn = () => {
  if (!isAuth0Configured) {
    return true;
  }

  const auth = inject(AuthService);
  return auth.isAuthenticated$.pipe(
    take(1),
    map((loggedIn) => {
      if (!loggedIn) {
        auth.loginWithRedirect();
        return false;
      }
      return true;
    }),
  );
};
