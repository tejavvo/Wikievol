import axios from 'axios';

// Base URL for the WikiEvolution backend API.
//
// In production the React SPA is served by the same Flask app, so the default
// empty string (i.e. same-origin relative paths) is correct.
//
// For local development, point the frontend at your local backend by creating
// a `client/.env` file with:
//   VITE_API_BASE_URL=http://localhost:5000
axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || '';
