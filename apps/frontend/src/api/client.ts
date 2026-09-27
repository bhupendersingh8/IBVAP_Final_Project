import axios from 'axios';

// Vite config proxies /api to localhost:8000 in dev
const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;
