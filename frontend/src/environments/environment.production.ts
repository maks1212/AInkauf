export const environment = {
  production: true,
  apiUrl: '/api',
  auth0: {
    domain: 'YOUR_AUTH0_DOMAIN.auth0.com',
    clientId: 'YOUR_AUTH0_CLIENT_ID',
    authorizationParams: {
      redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
    },
  },
};
