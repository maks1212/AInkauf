export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  auth0: {
    domain: 'YOUR_AUTH0_DOMAIN.auth0.com',
    clientId: 'YOUR_AUTH0_CLIENT_ID',
    authorizationParams: {
      redirect_uri: 'http://localhost:4200',
    },
  },
};
