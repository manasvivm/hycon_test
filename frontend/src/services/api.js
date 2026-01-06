import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with optimized settings
const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  timeout: 15000, // 15 second timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Add request interceptor to add token to all requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for better error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - redirect to login
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Configure axios defaults for backward compatibility
axios.defaults.baseURL = BASE_URL;
axios.defaults.withCredentials = true;

// Equipment API - using optimized apiClient
export const equipmentApi = {
  getAll: () => apiClient.get('/equipment'),
  getById: (id) => apiClient.get(`/equipment/${id}`),
  create: (data) => apiClient.post('/equipment', data),
  update: (id, data) => apiClient.put(`/equipment/${id}`, data),
  delete: (id) => apiClient.delete(`/equipment/${id}`),
  getDescriptionSuggestions: (query) => 
    apiClient.get(`/equipment/descriptions/suggestions?query=${query}`),
  batchUpload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post('/equipment/batch-upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    });
  }
};

// Session API - using optimized apiClient with retry logic for critical operations
export const sessionApi = {
  startSession: (data) => apiClient.post('/sessions/start', data),
  logPastUsage: (data) => apiClient.post('/sessions/log-past-usage', data),
  endSession: (sessionId, data) => apiClient.put(`/sessions/${sessionId}/end`, data),
  getMySessions: () => apiClient.get('/sessions/my-sessions'),
  getMyActiveSessions: () => apiClient.get('/sessions/my-active'),
  getMyActiveSession: () => apiClient.get('/sessions/my-active'),
  checkConflict: (data) => apiClient.post('/sessions/check-conflict', data),
};

// Analytics API - using optimized apiClient
export const analyticsApi = {
  getEquipmentUtilization: (startDate, endDate) => 
    apiClient.get(`/analytics/equipment-utilization?start_date=${startDate}&end_date=${endDate}`),
  getUserActivity: (startDate, endDate) =>
    apiClient.get(`/analytics/user-activity?start_date=${startDate}&end_date=${endDate}`),
  generateReport: (startDate, endDate) =>
    apiClient.get(`/analytics/generate-report?start_date=${startDate}&end_date=${endDate}`, 
      { responseType: 'blob', timeout: 30000 }), // Extended timeout for report generation
};

// User API - using optimized apiClient
export const userApi = {
  batchUpload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post('/auth/users/batch-upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    });
  }
};